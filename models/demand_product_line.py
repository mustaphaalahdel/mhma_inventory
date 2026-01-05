from odoo import _, models, fields, api
from odoo.exceptions import UserError


class DemandProductLine(models.Model):
    _name = 'mhma.demand.product.line'
    _description = 'Demand Product Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'demand_product_id'
    _order = 'sequence'
    
    active = fields.Boolean(default=True)
    
    sequence = fields.Integer(string='Sequence', default=10)
    
    approval_request_id = fields.Many2one(
        comodel_name='approval.request', 
        string='Approval Reference',
        domain="[('aprvl_type', 'in', ['0','1', '2', '3', '4', '5', '6'])]",
    )
    purchase_order_id = fields.Many2one(
        comodel_name='purchase.order', 
        string='Purchase Order',
    )
    confirmed_demand_product_lines = fields.Boolean(
        related='purchase_order_id.confirmed_demand_product_lines',
    )
    demand_product_id = fields.Many2one(
        required=True,
        comodel_name='mhma.demand.product', 
        string='Product',
    )
    desc = fields.Text(string='Description')
    qty = fields.Float(default=1)
    estimate_cost = fields.Float()
    uom_id = fields.Many2one(comodel_name='uom.uom', string='Unit of Measure')
    modified_qty = fields.Float(string='Modified Quantity', tracking = 1)
    modified_estimate_cost = fields.Float(string='Modified Estimate Cost', tracking = 1)
    total = fields.Float(
        compute='_compute_total',
        store=True,
    )
    modified_desc = fields.Text(string='Modified Description', tracking = 1)
    
    detail = fields.Html(string='Detail')
    modified_detail = fields.Html(string='Modified Detail')
    
    categ_id = fields.Many2one(related='demand_product_id.categ_id', string='Product Category')
    type = fields.Selection(related='demand_product_id.type', string='Type')
    request_owner_id = fields.Many2one(related='approval_request_id.request_owner_id', string='Request Owner')
    state = fields.Selection(related='approval_request_id.request_status', string='State')
    purchase_state = fields.Selection(
        related='purchase_order_id.state',
        string='Purchase Order State',
    )
    
    pending_user_id = fields.Many2one(
        related='approval_request_id.pending_user_id',
    )
    
    @api.depends('modified_qty', 'modified_estimate_cost')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.modified_qty * rec.modified_estimate_cost
    
    @api.onchange('demand_product_id')
    def _set_values(self):
        if self.demand_product_id:
            self.uom_id = self.demand_product_id.uom_id
            self.estimate_cost = self.demand_product_id.estimated_cost
            # self.modified_estimate_cost = self.demand_product_id.estimated_cost
            self.desc = self.demand_product_id.desc
            # self.modified_desc = self.demand_product_id.desc
            self.detail = self.demand_product_id.detail
            
    @api.onchange('qty')
    def _set_modified_qty(self):
        self.modified_qty = self.qty
            
    @api.onchange('estimate_cost')
    def _set_modified_estimate_cost(self):
        self.modified_estimate_cost = self.estimate_cost
            
    @api.onchange('desc')
    def _set_modified_desc(self):
        self.modified_desc = self.desc
        
    @api.onchange('detail')
    def _set_modified_detail(self):
        self.modified_detail = self.detail
            

    def unlink(self):
        for line in self:
            if line.state != 'new' and line.approval_request_id:
                raise UserError(_("Demand product line can only be deleted if the status is 'New'."))
            elif line.confirmed_demand_product_lines == True and line.purchase_order_id:
                raise UserError(_("Demand product line can only be deleted if the not confirmed.'."))
        return super().unlink()
    
    def action_view_tool(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Detail Demand Product Line',
            'res_model': 'mhma.demand.product.line',
            'view_mode': 'form',
            'view_id': self.env.ref('mhma_inventory.demand_product_line_form_detail').id,
            'res_id': self.id,
            'target': 'new',
        }
        
    def action_view_tool_to_purchase(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Detail Demand Product Line',
            'res_model': 'mhma.demand.product.line',
            'view_mode': 'form',
            'view_id': self.env.ref('mhma_inventory.demand_product_line_form_detail_in_purchase').id,
            'res_id': self.id,
            'target': 'new',
        }
        
    def write(self, vals):
        if vals.get('modified_detail'):
            if self.modified_detail != vals.get('modified_detail'):
                if self.env.user.lang == 'ar_001':
                    self.message_post(
                        body_is_html=True, 
                        body=f"تم تعديل حقل [التفاصيل المعدلة] من: {self.modified_detail} الى: {vals.get('modified_detail')}",
                    )
                else:
                    self.message_post(
                        body_is_html=True, 
                        body=f"Modified Field [Modified Detail] From: {self.modified_detail} To: {vals.get('modified_detail')}",
                    )
        return super().write(vals)
