from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    approval_request_id = fields.Many2one(
        comodel_name = 'approval.request', 
        string = 'Approval Request',
        domain = """
            [
                ('aprvl_type', '=', '10'), 
                ('request_status', '=', 'approved'), 
            ]
        """,
    )
    
    @api.onchange('approval_request_id')
    def _onchange_approval_request_id(self):
        for rec in self:
            if rec.approval_request_id:
                rec.name = rec.approval_request_id.partner_name
                rec.street = rec.approval_request_id.partner_address
                rec.email = rec.approval_request_id.partner_email
                rec.phone = rec.approval_request_id.partner_phone
                rec.mobile = rec.approval_request_id.partner_mobile
                rec.property_account_receivable_id = rec.approval_request_id.partner_debit_account_id
                rec.property_account_payable_id = rec.approval_request_id.partner_credit_account_id
    
    partner_type = fields.Selection(
        selection=[
            ('customer', 'Customer'), 
            ('vendor', 'Vendor'),
            ('both', 'Customer & Vendor'),
            ('employee', 'Employee'),
            ('never', 'Never')
        ], 
        default='never',
        string='Partner Type',
        change_default=True
    )
