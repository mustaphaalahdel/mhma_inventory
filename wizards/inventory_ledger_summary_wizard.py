from odoo import _, models, fields, api
from odoo.exceptions import UserError

class InventoryLedgerSummaryWizard(models.TransientModel):
    _name = 'inventory.ledger.summary.wizard'
    _description = 'Inventory Ledger Summary Wizard'

    name = fields.Char(string='Name')
    
    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            date_from_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(vals['date_from']))
            date_to_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(vals['date_to']))
            name = f"{date_from_local.replace(tzinfo=None)}::{date_to_local.replace(tzinfo=None)}"
            vals['name'] = name.replace(' ', '_')
        return super().create(vals_list)
    
    date_from = fields.Datetime(string='Date From', required=True)
    date_to = fields.Datetime(string='Date To', required=True)
    product_ids = fields.Many2many(
        comodel_name='product.product', 
        string='Products',
    )
    categ_ids = fields.Many2many(
        comodel_name='product.category', 
        string='Categories',
    )
    
    @api.onchange('categ_ids')
    def _onchange_categ_ids(self):
        self.product_ids = self.env['product.product'].search([
            ('categ_id', 'child_of', self.categ_ids.ids),
        ])
    
    line_ids = fields.One2many(
        comodel_name='inventory.ledger.summary.wizard.line',
        inverse_name='wizard_id',
        string='Lines'
    )
    

    def action_get_stock_summary(self):
        # إذا كان المستخدم اختار منتجات → نستخدمها، وإلا نجيب الكل
        products = self.product_ids if self.product_ids else self.env['product.product'].search([
            ('active', 'in', [True, False]),
        ])
        self.line_ids = [(5, 0, 0)]  # مسح أي بيانات سابقة
        
        result_lines = []

        for product in products:
            # جلب بيانات أستاذ المخزون من stock.valuation.layer
            ledger_lines = self.env['stock.valuation.layer'].search([
                ('product_id', '=', product.id),
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to),
            ], order='create_date asc')




            # if not ledger_lines:
            #     continue

	        # إذا لم توجد حركات تقييم خلال الفترة
            if not ledger_lines:
                # نتحقق هل المنتج لديه كمية في المخزون
                product_qty = product.qty_available  # أو quant حسب احتياجك
                if product_qty <= 0:
                    continue  # تجاهل المنتج لأنه بدون رصيد نهائي أو افتتاحي
                else:
                    # المنتج لديه كمية ولكن بدون تقييمات داخل الفترة
                    # نستخدم التكلفة الحالية (تكلفة قياسية أو متوسط)
                    standard_cost = product.standard_price or 0.0
                    closing_qty = product_qty
                    closing_cost = standard_cost
                    closing_val = closing_qty * closing_cost
                    result_lines.append((0, 0, {
                        'product_id': product.id,
                        'opening_qty': round(closing_qty, 2),
                        'opening_cost': round(closing_cost, 2),
                        'opening_val': round(closing_val, 2),
                        'inbound_qty': 0.0,
                        'inbound_cost': 0.0,
                        'inbound_val': 0.0,
                        'outbound_qty': 0.0,
                        'outbound_cost': 0.0,
                        'outbound_val': 0.0,
                        'closing_qty': round(closing_qty, 2),
                        'closing_cost': round(closing_cost, 2),
                        'closing_val': round(closing_val, 2),
                        'valuations_count': 0,
                        'stock_valuation_layer_ids': [(6, 0, [])],
                    }))
                    continue   # نكمل للمنتج التالي




            # أول يوم في الفترة → الافتتاحي
            opening_qty = ledger_lines[0].opening_qty
            opening_val = ledger_lines[0].opening_val

            # آخر يوم في الفترة → النهائي
            closing_qty = ledger_lines[-1].closing_qty
            closing_val = ledger_lines[-1].closing_val

            inbound_qty = sum(l.inbound_qty for l in ledger_lines)
            inbound_val = sum(l.inbound_val for l in ledger_lines)
            outbound_qty = sum(l.outbound_qty for l in ledger_lines)
            outbound_val = sum(l.outbound_val for l in ledger_lines)

            result_lines.append((0, 0, {
                'product_id': product.id,
                'opening_qty': round(opening_qty, 2),
                'opening_cost': round(opening_val / opening_qty, 2) if opening_qty else 0.0,
                'opening_val': round(opening_val, 2),
                'inbound_qty': round(inbound_qty, 2),
                'inbound_cost': round(inbound_val / inbound_qty, 2) if inbound_qty else 0.0,
                'inbound_val': round(inbound_val, 2),
                'outbound_qty': round(outbound_qty, 2),
                'outbound_cost': round(outbound_val / outbound_qty, 2) if outbound_qty else 0.0,
                'outbound_val': round(outbound_val, 2),
                'closing_qty': round(closing_qty, 2),
                'closing_cost': round(closing_val / closing_qty, 2) if closing_qty else 0.0,
                'closing_val': round(closing_val, 2),
                'valuations_count': len(ledger_lines),
                'stock_valuation_layer_ids': [(6, 0, ledger_lines.ids)],
            }))

        self.line_ids = result_lines
        
        date_from_local = fields.Datetime.context_timestamp(self, self.date_from).date()
        date_to_local = fields.Datetime.context_timestamp(self, self.date_to).date()

        return {
            'type': 'ir.actions.act_window',
            'name': f"{date_from_local}::{date_to_local}",
            'res_model': 'inventory.ledger.summary.wizard.line',
            'view_mode': 'tree,pivot',
            # 'view_id': self.env.ref('mhma_inventory.action_inventory_ledger_summary_line_tree').id,
            'views': [
                (self.env.ref('mhma_inventory.action_inventory_ledger_summary_line_tree').id, 'tree'),
                (self.env.ref('mhma_inventory.action_inventory_ledger_summary_line_pivot').id, 'pivot'),
            ],
            'res_id': self.id,
            'domain': [('wizard_id', '=', self.id)],
            'target': 'current',
        }


class InventoryLedgerSummaryWizardLine(models.TransientModel):
    _name = 'inventory.ledger.summary.wizard.line'
    _description = 'Inventory Ledger Summary Wizard Line'

    wizard_id = fields.Many2one('inventory.ledger.summary.wizard', string='Wizard')
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    categ_id = fields.Many2one(related='product_id.categ_id', string='Category', store=True)
    # product = fields.Char(string='Product', related='product_id.name')
    opening_qty = fields.Float(string='Opening Qty')
    opening_cost = fields.Float(string='Opening Cost')
    opening_val = fields.Float(string='Opening Value')
    inbound_qty = fields.Float(string='Inbound Qty')
    inbound_cost = fields.Float(string='Inbound Cost')
    inbound_val = fields.Float(string='Inbound Value')
    outbound_qty = fields.Float(string='Outbound Qty')
    outbound_cost = fields.Float(string='Outbound Cost')
    outbound_val = fields.Float(string='Outbound Value')
    closing_qty = fields.Float(string='Closing Qty')
    closing_cost = fields.Float(string='Closing Cost')
    closing_val = fields.Float(string='Closing Value')
    valuations_count = fields.Integer(string='Valuations Count')
    
    stock_valuation_layer_ids = fields.Many2many(
        comodel_name='stock.valuation.layer',
        string='Stock Valuation Layers', 
    )
    
    def action_view_tool(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _(f'Valuations'),
            'res_model': 'stock.valuation.layer',
            'view_mode': 'tree',
            'domain': [('id', 'in', self.stock_valuation_layer_ids.ids)],
            'view_id': self.env.ref('mhma_inventory.stock_valuation_layer_tree_simple').id,
            'target': 'current',
        }
        