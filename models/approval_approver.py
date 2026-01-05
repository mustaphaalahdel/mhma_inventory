
from odoo import _, models, fields, api


class ApprovalApprover(models.Model):
    _inherit = 'approval.approver'

    existing_request_user_ids = fields.Many2many('res.users', compute='_compute_existing_request_user_ids')

    @api.depends('request_id.request_owner_id', 'request_id.approver_ids.user_id')
    def _compute_existing_request_user_ids(self):
        for approver in self:
            approver.existing_request_user_ids = (
                approver.request_id.approver_ids.user_id._origin
            )
