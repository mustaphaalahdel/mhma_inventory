from odoo import _, models, fields, api
from odoo.exceptions import UserError

class StockMoveValuation(models.Model):
    _name = 'stock.valuation.layer'
    _inherit = ['stock.valuation.layer', 'mail.thread', 'mail.activity.mixin']
    
    
    active = fields.Boolean('Active', default=True, tracking=True)
    
    # quantity = fields.Float('Quantity', readonly=True, digits='Product Unit of Measure', tracking=True)
    # unit_cost = fields.Float('Unit Value', digits='Product Price', readonly=True, group_operator=None, tracking=True)
    # value = fields.Monetary('Total Value', readonly=True, tracking=True)
    # account_move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True, check_company=True, index="btree_not_null", tracking=True)
    account_move_state = fields.Selection(
        related='account_move_id.state', 
        string='Journal Entry Status', 
        readonly=True,
    )
    
    def unlink(self):
        for rec in self:
            if rec.active:
                raise UserError(_("You can't delete an active valuation layer. Archive it instead."))
        return super().unlink()
    
    # create_date = fields.Datetime('Date', readonly=True, index=True, default=fields.Datetime.now, tracking=True)
                
    avcost = fields.Float(
        string='Average Cost',
        readonly=True,
        store=True,
    )
    prev_avcost = fields.Float(
        string='Previous Average Cost',
        readonly=True,
        store=True,
    )
    
    def action_recompute_avcost(self):
        """إعادة حساب avcost و prev_avcost في استعلام SQL واحد باستخدام CTE"""
        query = """
            WITH calc AS (
                SELECT
                    id,
                    product_id,
                    create_date,
                    quantity,
                    CASE 
                        WHEN SUM(quantity) OVER (PARTITION BY product_id ORDER BY create_date, id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) = 0
                            THEN 0
                        ELSE
                            SUM(value) OVER (PARTITION BY product_id ORDER BY create_date, id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                            / NULLIF(SUM(quantity) OVER (PARTITION BY product_id ORDER BY create_date, id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 0)
                    END AS raw_avg_cost
                FROM stock_valuation_layer
            ),
            av AS (
                SELECT
                    id,
                    product_id,
                    create_date,
                    quantity,
                    CASE
                        WHEN raw_avg_cost = 0 AND quantity != 0
                            THEN LAG(NULLIF(raw_avg_cost,0)) OVER (PARTITION BY product_id ORDER BY create_date, id)
                        ELSE raw_avg_cost
                    END AS avcost
                FROM calc
            ),
            final AS (
                SELECT
                    id,
                    avcost,
                    COALESCE(LAG(avcost) OVER (PARTITION BY product_id ORDER BY create_date, id), 0) AS prev_avcost
                FROM av
            )
            UPDATE stock_valuation_layer svl
            SET avcost = final.avcost,
                prev_avcost = final.prev_avcost
            FROM final
            WHERE svl.id = final.id;
        """
        self.env.cr.execute(query)
        self.env.invalidate_all()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Done'),
                'message': _('Average cost and previous average cost calculated for all valuations in one query, please refresh the page'),
                'type': 'success',
                'sticky': False,
            }
        }

    
    
    avcost_value_total = fields.Float(
        string='Average Cost Value',
        readonly=True,
        store=True,
        compute='_compute_avcost_value_total',
    )
    @api.depends('avcost', 'quantity')
    def _compute_avcost_value_total(self):
        for rec in self:
            rec.avcost_value_total = rec.avcost * rec.quantity
    
    partner_id = fields.Many2one(
        related='stock_move_id.partner_id',
        string='Partner',
        readonly=True,
        store=True,
    )
    partner_move_id = fields.Many2one(
        related='stock_move_id.partner_move_id',
        string='Move Partner',
        readonly=True,
        store=True,
    )
    depart_id = fields.Many2one(
        related='stock_move_id.depart_id',
        string='Depart',
        readonly=True,
        store=True,
    )

    opening_qty = fields.Float(
        string='Opening Quantity',
        readonly=True,
        store=True,   # حتى نستطيع الفرز والبحث عليه
    )
    opening_val = fields.Float(
        string='Opening Value',
        readonly=True,
        store=True,
    )
    closing_qty = fields.Float(
        string='Closing Quantity',
        readonly=True,
        store=True,
    )
    closing_val = fields.Float(
        string='Closing Value',
        readonly=True,
        store=True,
    )
    
    
    qty_balances_computed = fields.Boolean(
        string='Balances Computed',
        default=False,
        store=True
    )

    def action_set_qty_balances_computed_false(self):
        query = """
            UPDATE stock_valuation_layer
            SET qty_balances_computed = FALSE
        """
        self.env.cr.execute(query)
        self.env.invalidate_all()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                # 'title': 'تم بنجاح',
                'title': _('Done'),
                # 'message': 'تم إعادة تعيين حالة احتساب الأرصدة لكل البنود، قم بعمل تحديث للصفحة',
                'message': _('The balance computation status has been reset for all records. Please refresh the page.'),
                'type': 'success',
                'sticky': False,
            }
        }

    # تم استبدال uznit_cost ب avcost
    def action_compute_qty_balances(self):
        """
        This method correctly recalculates balances only for products
        that have new, uncalculated layers.
        """
        query = """
            WITH products_to_update AS (
                -- Step 1: Find all products that have at least one uncomputed layer
                SELECT DISTINCT product_id
                FROM stock_valuation_layer
                WHERE qty_balances_computed IS NOT TRUE
            ),
            computed_balances AS (
                -- Step 2: Recalculate the ENTIRE history for ONLY those products
                SELECT
                    id,
                    quantity,
                    avcost,
                    prev_avcost,
                    SUM(quantity) OVER (
                        PARTITION BY product_id
                        ORDER BY create_date, id
                    ) AS running_total
                FROM
                    stock_valuation_layer
                WHERE
                    product_id IN (SELECT product_id FROM products_to_update)
            )
            -- Step 3: Update all layers for the affected products and set the flag
            UPDATE
                stock_valuation_layer sl
            SET
                closing_qty = cb.running_total,
                opening_qty = cb.running_total - sl.quantity,
                closing_val = cb.running_total * cb.avcost,
                opening_val = (cb.running_total - sl.quantity) * cb.prev_avcost,
                qty_balances_computed = TRUE
            FROM
                computed_balances cb
            WHERE
                sl.id = cb.id;
        """
    
        self.env.cr.execute(query)
        self.env.invalidate_all()

        # ... (return notification)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                # 'title': 'تم بنجاح',
                'title': _('Done'),
                # 'message': 'تم تحديث أرصدة البنود الجديدة قم بعمل تحديث للصفحة.',
                'message': _('The balances of the new records have been updated. Please refresh the page.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for record in records:
            
            record.write({
                'unit_cost_mhma': record.unit_cost,
                'qty_mhma': record.quantity,
                'value_mhma': record.value,
                'mhma_account_move_id': record.account_move_id.id if record.account_move_id else False,
                'mhma_create_date': record.create_date,
            })
            
            product = record.product_id
            if product.cost_method == 'average':
                print(f"product.standard_price: {product.standard_price}")
                if record.quantity == 0:
                    prev_valuation = product.qty_available * product.standard_price
                    print(f"prev_valuation = {product.qty_available} * {product.standard_price} = {prev_valuation}")
                    current_valuation = prev_valuation + record.value
                    print(f"current_valuation = {prev_valuation} + {record.value} = {current_valuation}")
                    record.avcost = current_valuation / (product.qty_available + record.quantity)
                    print(f"record.avcost = {current_valuation} / ({product.qty_available} + {record.quantity}) = {record.avcost}")  
                else:
                    record.avcost = product.standard_price              
            
            
            # البحث عن آخر بند تقييم سابق لهذا المنتج
            previous_layer = self.env['stock.valuation.layer'].search([
                ('product_id', '=', record.product_id.id),
                ('id', '<', record.id),
                ('qty_balances_computed', '=', True)
            ], order='create_date DESC, id DESC', limit=1)

            if previous_layer:
                opening = previous_layer.closing_qty
                record.prev_avcost = previous_layer.avcost
            else:
                opening = 0.0
                record.prev_avcost = 0.0

            record.opening_qty = opening
            record.closing_qty = opening + record.quantity
            

            record.opening_val = record.opening_qty * round(record.prev_avcost, 2)
            record.closing_val = record.closing_qty * round(record.avcost, 2)
            if record.opening_qty or record.closing_qty:
                record.qty_balances_computed = True
                

        return records

    inbound_qty = fields.Float(
        string='Inbound Quantity',
        readonly=True,
        store=True,
        compute='_compute_inbound_outbound_qty',
    )
    inbound_val = fields.Float(
        string='Inbound Value',
        readonly=True,
        store=True,
        compute='_compute_inbound_outbound_val',
    )
    
    outbound_qty = fields.Float(
        string='Outbound Quantity',
        readonly=True,
        store=True,
        compute='_compute_inbound_outbound_qty',
    )
    outbound_val = fields.Float(
        string='Outbound Value',
        readonly=True,
        store=True,
        compute='_compute_inbound_outbound_val',
    )
    
    @api.depends('quantity')
    def _compute_inbound_outbound_qty(self):
        for record in self:
            if record.quantity > 0:
                record.inbound_qty = record.quantity
                record.outbound_qty = 0.0
            else:
                record.inbound_qty = 0.0
                record.outbound_qty = -record.quantity
                
    @api.depends('avcost', 'unit_cost', 'inbound_qty', 'outbound_qty', 'quantity')
    def _compute_inbound_outbound_val(self):
        for record in self:
            # if record.unit_cost > 0:
            #     print(f"record.unit_cost: {record.unit_cost}")
            #     record.inbound_val = record.inbound_qty * record.unit_cost # يتم الضرب في unit_cost لانه توريد من مورد عن طريق الشراء فيكون سعر الوحدة
            # else:
            #     print(f"record.avcost: {record.avcost}")
            #     record.inbound_val = record.inbound_qty * record.avcost
            record.inbound_val = record.inbound_qty * round(record.unit_cost, 2)
            print(f"record.inbound_val = {record.inbound_qty} * {record.unit_cost} = {record.inbound_val}")
            record.outbound_val = record.outbound_qty * round(record.unit_cost, 2)
            
            if record.quantity == 0:
                diff_between_closing_and_opening = record.closing_val - record.opening_val
                if diff_between_closing_and_opening > 0:
                    record.inbound_val = diff_between_closing_and_opening
                else:
                    record.outbound_val = -diff_between_closing_and_opening
    
    
        
    
    # Inventory Ledger Summary
    
    def action_inventory_ledger_summary(self):
        
        

        self._compute_inbound_outbound_val()
        self.set_defalt_data()
        
        action = self.env['ir.actions.actions']._for_xml_id('mhma_inventory.inventory_ledger_summary_action')
        return action
    
    
    unit_cost_mhma = fields.Float(
        string='Unit Cost MHMA',
        # related='unit_cost',
        tracking=True,
        store=True,
        readonly=False,
    )
    qty_mhma = fields.Float(
        string='Quantity MHMA',
        # related='quantity',
        tracking=True,
        store=True,
        readonly=False
    )
    value_mhma = fields.Float(
        string='Value MHMA',
        # related='value',
        tracking=True,
        store=True,
        readonly=False
    )
    mhma_account_move_id = fields.Many2one(
        comodel_name='account.move',
        string='MHMA Account Move',
        tracking=True
    )
    mhma_create_date = fields.Datetime(
        string='MHMA Created At',
        tracking=True
    )
    @api.onchange('qty_mhma', 'unit_cost_mhma')
    def _onchange_qty_mhma_or_unit_cost_mhma(self):
        self.value_mhma = self.qty_mhma * self.unit_cost_mhma
    
    allow_edit = fields.Boolean(
        string='Allow Edit',
        default=False,
        tracking=True
    )
    
    @api.onchange('allow_edit')
    def _onchange_allow_edit(self):
        if self.allow_edit:
            self.unit_cost_mhma = self.unit_cost
            self.qty_mhma = self.quantity
            self.value_mhma = self.value
            self.mhma_account_move_id = self.account_move_id
            self.mhma_create_date = self.create_date
            
    def set_defalt_data(self):
        for rec in self:
            rec.unit_cost_mhma = rec.unit_cost
            rec.qty_mhma = rec.quantity
            rec.value_mhma = rec.value
            rec.mhma_account_move_id = rec.account_move_id
            rec.mhma_create_date = rec.create_date

    def write(self, vals):
        
        # لو كان المستخدم يحاول يعمل أرشفة (تغيير active إلى False)
        if 'active' in vals:
            for rec in self:
                allow_edit_actual = vals.get('allow_edit', rec.allow_edit)
                if rec.account_move_id:
                    if (
                        rec.account_move_state != 'cancel'
                        or rec.quantity != 0
                        or not allow_edit_actual
                    ):
                        raise UserError(_("You can't archive a non-canceled move with a non-zero quantity or without allow_edit."))
                
        # حفظ allow_edit لكل سجل قبل التحديث
        allow_edit_map = {}
        for rec in self:
            allow_edit = vals.get('allow_edit', rec.allow_edit)
            allow_edit_map[rec.id] = allow_edit
            print(f"allow_edit 1: {allow_edit}")

        # تحديث الحقول الأساسية لكل سجل إذا allow_edit True
        for rec in self:
            if allow_edit_map.get(rec.id):
                print(f"allow_edit 2: {allow_edit_map.get(rec.id)}")
                unit_cost = vals.get('unit_cost_mhma', rec.unit_cost_mhma)
                qty = vals.get('qty_mhma', rec.qty_mhma)
                value = vals.get('value_mhma', rec.value_mhma)
                account_move_id = vals.get('mhma_account_move_id', rec.mhma_account_move_id)
                create_date = vals.get('mhma_create_date', rec.mhma_create_date)

                # تحديث السجل الحالي فقط
                vals_to_update = {
                    'unit_cost': unit_cost,
                    'quantity': qty,
                    'value': value,
                    'account_move_id': account_move_id,
                }
                super(StockMoveValuation, rec).write(vals_to_update)

                # تعديل create_date عبر SQL
                rec.env.cr.execute("""
                    UPDATE stock_valuation_layer
                    SET create_date = %s
                    WHERE id = %s
                """, (create_date, rec.id))
                rec.invalidate_recordset()  # تحديث الكاش للسجل فقط

        result = super().write(vals)

        # إعادة حساب تكلفة المنتج بعد التغييرات
        for rec in self:
            if allow_edit_map.get(rec.id) and rec.product_id:
                all_layers = self.env['stock.valuation.layer'].search([('product_id', '=', rec.product_id.id)])
                total_value = sum(all_layers.mapped('value'))
                total_qty = sum(all_layers.mapped('quantity'))
                new_cost = total_value / total_qty if total_qty else 0.0
                rec.product_id.sudo().write({'standard_price': new_cost})

        # 🔹 إرجاع allow_edit إلى False بعد الانتهاء
        for rec in self:
            if allow_edit_map.get(rec.id):
                rec.allow_edit = False

        # إعادة recordset بعد كتابة أي حقول أخرى في vals
        return result


    
    def action_transfer_to_stock_valuation_layer_form(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Stock Valuation Layer"),
            "res_model": "stock.valuation.layer",
            "res_id": self.id,  # يفتح السجل الحالي
            "view_mode": "form",
            "views": [(self.env.ref("mhma_inventory.stock_valuation_layer_form_simple").id, "form")],
            "target": "current",  # يفتح في نفس النافذة
        }
    

