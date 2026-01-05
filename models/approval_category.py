from odoo import _, models, fields, api
from odoo.exceptions import ValidationError

class ApprovalCategory(models.Model):
    _inherit = "approval.category"

    aprvl_type = fields.Selection(
        string="Type",
        selection=[
            ('0', 'Disbursement'),
            ('1', 'Request Purchase'),
            ('2', 'Determine items specifications'),
            ('3', 'Purchasing Directive'),
            ('4', 'Disbursing Directive'),
            
            ('5', 'Service Directive'),
            ('6', 'Maintenance Directive'),
            
            ('10', 'Request Add Partner'),
        ]
    )

    access_group_ids = fields.Many2many(
        comodel_name='res.groups', 
        relation='approval_category_group_rel',
        column1='category_id',
        column2='group_id',
        string="Access Groups",
        default=lambda self:self.env[ 'res.groups' ].search([('id', '=', '1')]).ids
    )

    symbol = fields.Char(string="Symbol")

    # symbol is unique for each category
    @api.constrains('symbol')
    def _check_symbol(self):
        for rec in self:
            if rec.symbol:
                if self.search([('id', '!=', rec.id), ('symbol', '=', rec.symbol)]):
                    raise ValidationError(_("Symbol must be unique"))

    manager_manager_approval = fields.Boolean(string="Manager Manager Approval")
    manager_manager_manager_approval = fields.Boolean(string="Manager Manager Manager Approval")

    @api.onchange("automated_sequence")
    def _set_sequence(self):
        for rec in self:
            if rec.automated_sequence:
                rec.symbol = False