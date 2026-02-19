from odoo import _, Command, models, fields, api
from odoo.exceptions import UserError, ValidationError

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    employee_recipient_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee recipient',
        compute='_compute_employee_recipient_id',
    )

    @api.depends('employee_id')
    def _compute_employee_recipient_id(self):
        for rec in self:
            rec.employee_recipient_id = rec.employee_id

    employee_recipient_user_id = fields.Many2one(
        comodel_name='res.users',
        string='Employee recipient User',
        related='employee_recipient_id.user_id',
        # compute='_compute_employee2_user_id',
    )
    # @api.depends('employee_recipient_id')
    # def _compute_employee2_user_id(self):
    #     for rec in self:
    #         rec.employee2_user_id = rec.employee_recipient_id.user_id

    approval_direct_purchase_id = fields.Many2one(
        comodel_name='approval.request', 
        string='Approval Direct Purchase',
        tracking=True,
        domain="[('aprvl_type', 'in', ['1', '2', '3']), ('request_status', 'in', ['approved', 'pending'])]",
    )

    approval_request_need_id = fields.Many2one(
        comodel_name='approval.request',
        # related='approval_direct_purchase_id.dsbrs_id',
        string='Approval Request Need',
        store=True,
        readonly=True,
    )

    beneficiary_id = fields.Many2one(
        comodel_name='res.partner',
        string='Beneficiary',
        tracking=True,
    )
    recipient_id = fields.Many2one(
        comodel_name='res.users',
        string='Recipient',
        tracking=True,
    )
    supplier_id = fields.Many2one(
        comodel_name='res.partner',
        string='Supplier',
        tracking=True,
    )
    
    @api.onchange('beneficiary_id')
    def _onchange_beneficiary_id(self):
        for rec in self:
            if rec.beneficiary_id and rec.beneficiary_id.user_ids:
                rec.recipient_id = rec.beneficiary_id.user_ids[0]

    @api.onchange('approval_direct_purchase_id')
    def _onchange_approval_direct_purchase_id(self):
        for rec in self:
            name = ""
            rec.beneficiary_id = False
            rec.total_amount_currency = 0
            if rec.approval_direct_purchase_id.dsbrs_id and rec.approval_direct_purchase_id.dsbrs_id.request_owner_id:
                rec.beneficiary_id = rec.approval_direct_purchase_id.dsbrs_id.request_owner_id.partner_id
                rec.approval_request_need_id = rec.approval_direct_purchase_id.dsbrs_id

            if rec.approval_direct_purchase_id.req_purchase_id and rec.approval_direct_purchase_id.req_purchase_id.dsbrs_id and rec.approval_direct_purchase_id.req_purchase_id.dsbrs_id.request_owner_id:
                rec.beneficiary_id = rec.approval_direct_purchase_id.req_purchase_id.dsbrs_id.request_owner_id.partner_id
                rec.approval_request_need_id = rec.approval_direct_purchase_id.req_purchase_id.dsbrs_id

            if rec.approval_direct_purchase_id:
                for line in rec.approval_direct_purchase_id.demand_product_line_ids:
                    # trim symbol + from name
                    name = name + (
                        f"+{line.demand_product_id.name} "
                        f"{line.modified_desc or ''}"
                        f"({line.modified_qty} {line.uom_id.name})"
                    )
                    name = name.rstrip('+').lstrip('+')
            rec.name = name
            rec.total_amount_currency = rec.approval_direct_purchase_id.total_all

            # if rec.approval_direct_purchase_id.aprvl_type != '2':
            #     rec.description = rec.approval_direct_purchase_id.reason
            # else:
            #     rec.description = rec.approval_direct_purchase_id.determine_specifications

    reminder_recipient = fields.Boolean('Reminder Recipient')
    confirm_receipt = fields.Boolean('Confirm Receipt')
            
    def action_reminder_recipient(self):
        for rec in self:
            rec.reminder_recipient = True
            if rec.recipient_id:
                # arabic
                if rec.env.user.lang and rec.env.user.lang.startswith('ar'):
                    rec.activity_schedule(
                        act_type_xmlid='mail.mail_activity_data_todo',
                        summary='قم بالتأكيد عند استلام الطلب',
                        user_id=rec.recipient_id.id,
                        note='يرجى مراجعة الطلب وتأكيد استلامه.'
                    )
                else:
                    rec.activity_schedule(
                        act_type_xmlid='mail.mail_activity_data_todo',
                        summary='Confirm receipt of the order.',
                        user_id=rec.recipient_id.id,
                        note='Please review the order and confirm receipt.'
                    )
    def action_confirm_receipt(self):
        for rec in self:
            activities = self.sudo().activity_ids.filtered(lambda act: act.user_id == self.env.user)
            rec.confirm_receipt = True
            # arabic
            if rec.env.user.lang and rec.env.user.lang.startswith('ar'):
                activities.action_feedback(
                    feedback=_(f"تم تاكيد استلام الطلب"),
                )
            else:
                activities.action_feedback(
                    feedback=_(f"The order has been confirmed."),
                )

