from odoo import _, models, fields, api
from odoo.exceptions import UserError

class ApprovalRejectionReason(models.TransientModel):
    _name = 'mhma.approval.rejection.reason'
    _description = 'Approval Rejection Reason'

    approval_request_id = fields.Many2one(
        'approval.request', 
        'Approval Request', 
        required=True,
        readonly=True,
    )
    request_owner_id = fields.Many2one(
        'res.users', 
        'Request Owner', 
        related='approval_request_id.request_owner_id',
        readonly=True,
    )
    rejection_reason = fields.Text('Rejection Reason', required=True)
    
    def action_reject(self):
        print(f"action_reject wizard: action_reject wizard")
        self.approval_request_id.action_refuse()
        self.approval_request_id.message_post(
            body=f"{self.rejection_reason}",  # نص الرسالة
            message_type='comment',  # نوع الرسالة (تعليق/رسالة)
            subtype_xmlid='mail.mt_comment',  # هذا يضمن إرسالها للمتابعين
            # partner_ids=[self.approval_request_id.request_owner_id.partner_id.id]
        )
    