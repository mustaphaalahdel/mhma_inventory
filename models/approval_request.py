from odoo import _, Command, models, fields, api
from odoo.exceptions import UserError, ValidationError
import re


class ApprovalRequest(models.Model):
    _inherit = ['approval.request']

    active = fields.Boolean(default=True, tracking=True)
    
    category_id = fields.Many2one('approval.category', string="Category", required=True, tracking=True)
    
    statement_subject = fields.Char(
        string='Statement Subject',
        tracking=True,
    )

    demand_product_line_ids = fields.One2many(
        comodel_name='mhma.demand.product.line', 
        inverse_name='approval_request_id', 
    )
    
    purchase_order_dis_ids = fields.One2many(
        comodel_name='purchase.order', 
        inverse_name='approval_purchase_specifications_id', 
    )
    purchase_order_pr_ids = fields.One2many(
        comodel_name='purchase.order', 
        inverse_name='approval_purchase_request_id', 
    )
    
    purchase_order_ids = fields.One2many(
        comodel_name="purchase.order",
        inverse_name="request_ref_id",
    )

    stock_picking_ids = fields.One2many(
        comodel_name='stock.picking', 
        inverse_name='approval_id', 
        string="Stock Pickings",
    )
    len_stock_picking_ids = fields.Integer(compute='_compute_len_stock_picking_ids')
    @api.depends('stock_picking_ids')
    def _compute_len_stock_picking_ids(self):
        for rec in self:
            if rec.stock_picking_ids:
                for stock_picking in rec.stock_picking_ids:
                    if stock_picking.state == 'assigned':
                        rec.len_stock_picking_ids = rec.len_stock_picking_ids + 1
                    else:
                        rec.len_stock_picking_ids = 0
            else:
                rec.len_stock_picking_ids = 0

    stock_picking_dd_ids = fields.One2many(
        comodel_name='stock.picking', 
        inverse_name='approval_disbursing_directive_id', 
        string="Stock Pickings DD",
    )
    len_stock_picking_dd_ids = fields.Integer(compute='_compute_len_stock_picking_dd_ids')
    @api.depends('stock_picking_dd_ids')
    def _compute_len_stock_picking_dd_ids(self):
        for rec in self:
            if rec.stock_picking_dd_ids:
                for stock_picking_dd in rec.stock_picking_dd_ids:
                    if stock_picking_dd.state == 'assigned':
                        rec.len_stock_picking_dd_ids = rec.len_stock_picking_dd_ids + 1
                    else:
                        rec.len_stock_picking_dd_ids = 0
            else:
                rec.len_stock_picking_dd_ids = 0

    depart_id = fields.Many2one(
        comodel_name="hr.department", 
        string='Department', 
        store=True, 
        compute='_compute_depart_id', 
        readonly=0, 
        copy=True,
        tracking=True,
    )

    @api.depends('request_owner_id',)
    def _compute_depart_id(self):
        for rec in self:
            if rec.request_owner_id.employee_ids:    
                rec.depart_id = rec.request_owner_id.employee_ids[0].department_id


    aprvl_type = fields.Selection(related='category_id.aprvl_type')

    dsbrs_id = fields.Many2one(
        comodel_name='approval.request',
        domain="['&', ('request_status', 'in', ['approved', 'refused', 'pending']), ('aprvl_type', '=', '0')]",
        ondelete='set null',
        tracking=True,
    )

    dsbrs_ids = fields.One2many(
        comodel_name='approval.request',
        inverse_name='dsbrs_id',
        order="create_date desc",
        string="Directions",
    )

    req_purchase_id = fields.Many2one(
        comodel_name='approval.request',
        string="Request Purchase",
        domain="[('aprvl_type', '=', '1'), ('request_status', '=', 'approved')]",
        ondelete='set null',
        tracking=True,
    )
    
    req_purchase_ids = fields.One2many(
        comodel_name='approval.request',
        inverse_name='req_purchase_id',
        order="create_date desc",
        string="Determine specifications",
    )

    notes = fields.Html(
        string="Notes", 
        store=True, 
        # compute='_set_notes', 
        readonly=False
    )
    determine_specifications = fields.Html('Determine Specifications', tracking=False)

    @api.onchange("dsbrs_id", "req_purchase_id")
    def _set_reason(self):
        for rec in self:
            if (
                (rec.aprvl_type == '0' and rec.dsbrs_id) 
                or (rec.aprvl_type == '1' and rec.dsbrs_id)
                or (rec.aprvl_type == '3' and rec.dsbrs_id)
                or (rec.aprvl_type == '4' and rec.dsbrs_id)
                or (rec.aprvl_type == '5' and rec.dsbrs_id)
                or (rec.aprvl_type == '6' and rec.dsbrs_id)
            ):
                rec.reason = rec.dsbrs_id.reason
                # rec.demand_product_line_ids = rec.dsbrs_id.demand_product_line_ids
                # clear existing lines
                rec.demand_product_line_ids  = [(5, 0, 0)]
                rec.demand_product_line_ids = [
                        (0, 0, {
                            'demand_product_id': line.demand_product_id.id,
                            'qty': line.modified_qty,
                            'uom_id': line.uom_id.id,
                            'desc': line.modified_desc,
                            'detail': line.modified_detail,
                            'estimate_cost': line.modified_estimate_cost,
                            'modified_desc': line.modified_desc,
                            'modified_qty': line.modified_qty,
                            'modified_estimate_cost': line.modified_estimate_cost,
                            'modified_detail': line.modified_detail,
                            # أضف باقي الحقول التي تريد نسخها
                        }) for line in rec.dsbrs_id.demand_product_line_ids
                    ]
            if (rec.aprvl_type == '2' and rec.req_purchase_id):
                rec.reason = rec.req_purchase_id.reason
                # rec.demand_product_line_ids = rec.req_purchase_id.demand_product_line_ids
                # clear existing lines
                rec.demand_product_line_ids  = [(5, 0, 0)]
                rec.demand_product_line_ids = [
                        (0, 0, {
                            'demand_product_id': line.demand_product_id.id,
                            'qty': line.modified_qty,
                            'uom_id': line.uom_id.id,
                            'desc': line.modified_desc,
                            'detail': line.modified_detail,
                            'estimate_cost': line.modified_estimate_cost,
                            'modified_desc': line.modified_desc,
                            'modified_qty': line.modified_qty,
                            'modified_estimate_cost': line.modified_estimate_cost,
                            'modified_detail': line.modified_detail,
                            # أضف باقي الحقول التي تريد نسخها
                        }) for line in rec.req_purchase_id.demand_product_line_ids
                    ]

    # @api.depends("dsbrs_id", "req_purchase_id")
    # def _set_notes(self):
    #     for rec in self:

    #         if (
    #             (rec.aprvl_type == '0' and rec.dsbrs_id) 
    #             or (rec.aprvl_type == '1' and rec.dsbrs_id)
    #             or (rec.aprvl_type == '3' and rec.dsbrs_id)
    #             or (rec.aprvl_type == '4' and rec.dsbrs_id)
    #         ):
                
    #             messages_approval_request = self.env['mail.message'].search(
    #                 ['&', ('res_id', '=', rec.dsbrs_id.id), ('model', '=', 'approval.request')],
    #                 order = 'create_date asc',
    #             )
    #             approvers_notes = ""
    #             for message in messages_approval_request:
    #                 if message.message_type == 'comment':
    #                     body = re.sub(r"<.*?>", "", message.body)

    #                     approvers_notes = f"""{approvers_notes}
    #                     <tr>
    #                         <td><p>{message.author_id.name}</p></td>
    #                         <td><p>{body}</p></td>
    #                         <td><p>{message.write_date}</p></td>
    #                     </tr>"""

    #             if approvers_notes != "":
    #                 if (self.env.user.lang == 'ar_001'):
    #                     approvers_notes = f"""<table class="table table-bordered o_table">
    #                         <tbody>
    #                             <tr>
    #                                 <td><strong><p>المعتمد</p></strong></td>
    #                                 <td><p><strong>الملاحظة</strong></p></td>
    #                                 <td><p><strong>التاريخ</strong></p></td>
    #                             </tr>
    #                             {approvers_notes}
    #                         </tbody>
    #                     </table>"""
    #                 else:
    #                     approvers_notes = f"""<table class="table table-bordered o_table">
    #                         <tbody>
    #                             <tr>
    #                                 <td><strong><p>Approver</p></strong></td>
    #                                 <td><p><strong>Note</strong></p></td>
    #                                 <td><p><strong>Date</strong></p></td>
    #                             </tr>
    #                             {approvers_notes}
    #                         </tbody>
    #                     </table>"""

    #             approvers = ""
    #             for user in rec.dsbrs_id.approver_ids:
    #                 if user.status == "approved":
    #                     if (self.env.user.lang == 'ar_001'):
    #                         approvers = f"{approvers}<li>{user.user_id.name} بتاريخ {user.write_date}</li>"
    #                     else:
    #                         approvers = f"{approvers}<li>{user.user_id.name} In Date {user.write_date}</li>"
    #             approvers = f"<ul>{approvers}</ul>"

    #             if (self.env.user.lang == 'ar_001'):
    #                 rec.notes = f"""<p><strong>حسب طلب الاحتياج:</strong></p> {rec.dsbrs_id.reason}
    #                 <p><strong>مرجع طلب الاحتياج:</strong> {rec.dsbrs_id.name}, <strong>تاريخ طلب الاحتياج:</strong> {rec.dsbrs_id.date_confirmed}</p>
    #                 <p><strong>مقدم طلب الاحتياج:</strong> {rec.dsbrs_id.request_owner_id.name}</p>
    #                 <p><strong>ملاحظات معتمدين طلب الاحتياج:</strong></p> {approvers_notes}
    #                 <p><strong>معتمدين طلب الاحتياج:</strong></p> {approvers}"""
    #             else:
    #                 rec.notes = f"""<p><strong>As per the requisition request:</strong></p> {rec.dsbrs_id.reason}
    #                 <p><strong>Requisition request reference:</strong> {rec.dsbrs_id.name}, <strong>Requisition request date:</strong> {rec.dsbrs_id.date_confirmed}</p>
    #                 <p><strong>Requisition request submitter:</strong> {rec.dsbrs_id.request_owner_id.name}</p>
    #                 <p><strong>Requisition request approvers notes:</strong></p> {approvers_notes}
    #                 <p><strong>Requisition request approvers:</strong></p> {approvers}"""

    #         elif rec.aprvl_type == '2' and rec.req_purchase_id:
    #             rec.determine_specifications = rec.req_purchase_id.reason
    #             messages_approval_request = self.env['mail.message'].search(
    #                 ['&', ('res_id', '=', rec.req_purchase_id.id), ('model', '=', 'approval.request')],
    #                 order = 'create_date asc',
    #             )
    #             approvers_notes = ""
    #             for message in messages_approval_request:
    #                 if message.message_type == 'comment':
    #                     body = re.sub(r"<.*?>", "", message.body)
    #                     approvers_notes = f"""{approvers_notes}
    #                     <tr>
    #                         <td><p>{message.author_id.name}</p></td>
    #                         <td><p>{body}</p></td>
    #                         <td><p>{message.write_date}</p></td>
    #                     </tr>"""
    #             if approvers_notes != "":
    #                 if (self.env.user.lang == 'ar_001'):
    #                     approvers_notes = f"""<table class="table table-bordered o_table">
    #                         <tbody>
    #                             <tr>
    #                                 <td><strong><p>المعتمد</p></strong></td>
    #                                 <td><p><strong>الملاحظة</strong></p></td>
    #                                 <td><p><strong>التاريخ</strong></p></td>
    #                             </tr>
    #                             {approvers_notes}
    #                         </tbody>
    #                     </table>"""
    #                 else:
    #                     approvers_notes = f"""<table class="table table-bordered o_table">
    #                         <tbody>
    #                             <tr>
    #                                 <td><strong><p>Approver</p></strong></td>
    #                                 <td><p><strong>Note</strong></p></td>
    #                                 <td><p><strong>Date</strong></p></td>
    #                             </tr>
    #                             {approvers_notes}
    #                         </tbody>
    #                     </table>"""

    #             approvers = ""
    #             for user in rec.req_purchase_id.approver_ids:
    #                 if user.status == "approved":
    #                     if (self.env.user.lang == 'ar_001'):
    #                         approvers = f"{approvers}<li>{user.user_id.name} بتاريخ {user.write_date}</li>"
    #                     else:
    #                         approvers = f"{approvers}<li>{user.user_id.name} In Date {user.write_date}</li>"
    #             approvers = f"""<ul>{approvers}</ul>"""

    #             if (self.env.user.lang == 'ar_001'):
    #                 rec.notes = f"""<p><strong>حسب طلب الشراء:</strong></p> {rec.req_purchase_id.reason}
    #                 <p><strong>مرجع طلب الشراء:</strong> {rec.req_purchase_id.name}, <strong>تاريخ طلب الشراء:</strong> {rec.req_purchase_id.date_confirmed}</p>
    #                 <p><strong>مقدم طلب الشراء:</strong> {rec.req_purchase_id.request_owner_id.name}</p>
    #                 <p><strong>ملاحظات معتمدين طلب الشراء:</strong></p> {approvers_notes}
    #                 <p><strong>معتمدين طلب الشراء:</strong></p> {approvers}"""
    #             else:
    #                 rec.notes = f"""<p><strong>As per the purchase request:</strong></p> {rec.req_purchase_id.reason}
    #                 <p><strong>Purchase request reference:</strong> {rec.req_purchase_id.name}, <strong>Purchase request date:</strong> {rec.req_purchase_id.date_confirmed}</p>
    #                 <p><strong>Purchase request submitter:</strong> {rec.req_purchase_id.request_owner_id.name}</p>
    #                 <p><strong>Purchase request approvers notes:</strong></p> {approvers_notes}
    #                 <p><strong>Purchase request approvers:</strong></p> {approvers}"""  
    #         else:
    #             rec.notes = ''
    #             # rec.determine_specifications = ''

    def write(self, vals):
        if vals.get('determine_specifications'):
            if self.determine_specifications != vals.get('determine_specifications'):
                if self.env.user.lang == 'ar_001':
                    self.message_post(
                        body_is_html=True, 
                        body=f"تم التعديل من: {self.determine_specifications} الى: {vals.get('determine_specifications')}",
                    )
                else:
                    self.message_post(
                        body_is_html=True, 
                        body=f"Modified From: {self.determine_specifications} To: {vals.get('determine_specifications')}",
                    )
        return super().write(vals)

    def action_print_approval_request_report(self):
        self.ensure_one()
        return self.env.ref('mhma_inventory.report_approval_request_pdf').report_action(self)

    def action_purchasing_directive(self):
        self.ensure_one()
        approval_category = self.env['approval.category'].search([('aprvl_type', '=', '3')], limit=1)
        dsbrs_ids_len = len(self.dsbrs_ids) + 1
        if approval_category:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Purchasing Directive'),
                'res_model': 'approval.request',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_name': f"{approval_category.symbol}-{dsbrs_ids_len}-{self.name}",
                    'default_category_id': approval_category.id,
                    'default_dsbrs_id': self.id,
                    'default_request_owner_id': self.env.user.id,
                    # 'default_demand_product_line_ids': [
                    #     (0, 0, {
                    #         'demand_product_id': line.demand_product_id.id,
                    #         'qty': line.modified_qty,
                    #         'uom_id': line.uom_id.id,
                    #         'desc': line.modified_desc,
                    #         'detail': line.modified_detail,
                    #         'estimate_cost': line.modified_estimate_cost,
                    #         'modified_desc': line.modified_desc,
                    #         'modified_qty': line.modified_qty,
                    #         'modified_estimate_cost': line.modified_estimate_cost,
                    #         'modified_detail': line.modified_detail,
                    #         # أضف باقي الحقول التي تريد نسخها
                    #     }) for line in self.demand_product_line_ids
                    # ],
                    # 'default_reason': self.reason,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Purchase directive category is not exists"),
                    'type': 'warning',
                    'message': _("Purchase directive category not configured."),
                    'sticky': True,
                },
            }

    def action_disbursing_directive(self):
        self.ensure_one()
        approval_category = self.env['approval.category'].search([('aprvl_type', '=', '4')], limit=1)
        dsbrs_ids_len = len(self.dsbrs_ids) + 1
        if approval_category:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Disbursing Directive'),
                'res_model': 'approval.request',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_name': f"{approval_category.symbol}-{dsbrs_ids_len}-{self.name}",
                    'default_category_id': approval_category.id,
                    'default_dsbrs_id': self.id,
                    'default_request_owner_id': self.env.user.id,
                    # 'default_demand_product_line_ids': [
                    #     (0, 0, {
                    #         'demand_product_id': line.demand_product_id.id,
                    #         'qty': line.modified_qty,
                    #         'uom_id': line.uom_id.id,
                    #         'desc': line.modified_desc,
                    #         'estimate_cost': line.modified_estimate_cost,
                    #         'detail': line.modified_detail,
                    #         'modified_desc': line.modified_desc,
                    #         'modified_qty': line.modified_qty,
                    #         'modified_estimate_cost': line.modified_estimate_cost,
                    #         'modified_detail': line.modified_detail,
                    #         # أضف باقي الحقول التي تريد نسخها
                    #     }) for line in self.demand_product_line_ids
                    # ],
                    # 'default_reason': self.reason,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Disbursing directive category is not exists"),
                    'type': 'warning',
                    'message': _("Disbursing directive category not configured."),
                    'sticky': True,
                },
            }


    def action_service_directive(self):
        self.ensure_one()
        approval_category = self.env['approval.category'].search([('aprvl_type', '=', '5')], limit=1)
        dsbrs_ids_len = len(self.dsbrs_ids) + 1
        if approval_category:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Service Directive'),
                'res_model': 'approval.request',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_name': f"{approval_category.symbol}-{dsbrs_ids_len}-{self.name}",
                    'default_category_id': approval_category.id,
                    'default_dsbrs_id': self.id,
                    'default_request_owner_id': self.env.user.id,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Service directive category is not exists"),
                    'type': 'warning',
                    'message': _("Service directive category not configured."),
                    'sticky': True,
                },
            }
    def action_purchase_request(self):
        self.ensure_one()
        approval_category = self.env['approval.category'].search([('aprvl_type', '=', '1')], limit=1)
        dsbrs_ids_len = len(self.dsbrs_ids) + 1
        if approval_category:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Purchase Request'),
                'res_model': 'approval.request',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_name': f"{approval_category.symbol}-{dsbrs_ids_len}-{self.name}",
                    'default_category_id': approval_category.id,
                    'default_dsbrs_id': self.id,
                    'default_request_owner_id': self.env.user.id,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Purchase Request category is not exists"),
                    'type': 'warning',
                    'message': _("Purchase Request category not configured."),
                    'sticky': True,
                },
            }
    def action_determine_specifications(self):
        self.ensure_one()
        approval_category = self.env['approval.category'].search([('aprvl_type', '=', '2')], limit=1)
        req_purchase_ids_len = len(self.req_purchase_ids) + 1
        if approval_category:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Determine Specifications'),
                'res_model': 'approval.request',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_name': f"{approval_category.symbol}-{req_purchase_ids_len}-{self.name}",
                    'default_category_id': approval_category.id,
                    'default_req_purchase_id': self.id,
                    'default_request_owner_id': self.env.user.id,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Determine specifications category is not exists"),
                    'type': 'warning',
                    'message': _("Determine specifications category not configured."),
                    'sticky': True,
                },
            }


    def action_maintenance_directive(self):
        self.ensure_one()
        approval_category = self.env['approval.category'].search([('aprvl_type', '=', '6')], limit=1)
        dsbrs_ids_len = len(self.dsbrs_ids) + 1
        if approval_category:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Maintenance Directive'),
                'res_model': 'approval.request',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_name': f"{approval_category.symbol}-{dsbrs_ids_len}-{self.name}",
                    'default_category_id': approval_category.id,
                    'default_dsbrs_id': self.id,
                    'default_request_owner_id': self.env.user.id,
                    # 'default_demand_product_line_ids': [
                    #     (0, 0, {
                    #         'demand_product_id': line.demand_product_id.id,
                    #         'qty': line.modified_qty,
                    #         'uom_id': line.uom_id.id,
                    #         'desc': line.modified_desc,
                    #         'estimate_cost': line.modified_estimate_cost,
                    #         'detail': line.modified_detail,
                    #         'modified_desc': line.modified_desc,
                    #         'modified_qty': line.modified_qty,
                    #         'modified_estimate_cost': line.modified_estimate_cost,
                    #         'modified_detail': line.modified_detail,
                    #         # أضف باقي الحقول التي تريد نسخها
                    #     }) for line in self.demand_product_line_ids
                    # ],
                    # 'default_reason': self.reason,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Maintenance directive category is not exists"),
                    'type': 'warning',
                    'message': _("Maintenance directive category not configured."),
                    'sticky': True,
                },
            }



    def action_purchase_rfq(self):
        self.ensure_one()
        if self.aprvl_type == '2':
            return {
                'type': 'ir.actions.act_window',
                'name': _('Purchase RFQ'),
                'res_model': 'purchase.order',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_approval_purchase_specifications_id': self.id,
                    # 'default_demand_product_line_ids': [
                    #     (0, 0, {
                    #         'demand_product_id': line.demand_product_id.id,
                    #         'qty': line.modified_qty,
                    #         'uom_id': line.uom_id.id,
                    #         'desc': line.modified_desc,
                    #         'detail': line.modified_detail,
                    #         'estimate_cost': line.modified_estimate_cost,
                    #         'modified_desc': line.modified_desc,
                    #         'modified_qty': line.modified_qty,
                    #         'modified_estimate_cost': line.modified_estimate_cost,
                    #         'modified_detail': line.modified_detail,
                    #         # أضف باقي الحقول التي تريد نسخها
                    #     }) for line in self.demand_product_line_ids
                    # ]
                }
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Purchase RFQ'),
                'res_model': 'purchase.order',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_approval_purchase_request_id': self.id,
                    # 'default_demand_product_line_ids': [
                    #     (0, 0, {
                    #         'demand_product_id': line.demand_product_id.id,
                    #         'qty': line.modified_qty,
                    #         'uom_id': line.uom_id.id,
                    #         'desc': line.modified_desc,
                    #         'detail': line.modified_detail,
                    #         'estimate_cost': line.modified_estimate_cost,
                    #         'modified_desc': line.modified_desc,
                    #         'modified_qty': line.modified_qty,
                    #         'modified_estimate_cost': line.modified_estimate_cost,
                    #         'modified_detail': line.modified_detail,
                    #         # أضف باقي الحقول التي تريد نسخها
                    #     }) for line in self.demand_product_line_ids
                    # ]
                }
            }

    def action_direct_purchase(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Direct Purchase'),
            'res_model': 'hr.expense',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_approval_direct_purchase_id': self.id,
            }
        }

    def action_disburse_commend(self):
        self.ensure_one()
        picking_type = self.env['stock.picking.type'].search(
            [
                ('code', '=', 'outgoing'),
                ('sequence_code', '=', 'dsbrs'),
            ], limit=1)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Disburse Commend'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_picking_type_id': picking_type.id,
                'default_approval_disbursing_directive_id': self.id,
            }
        }

    @api.model
    def _create_or_update_approver(self, user_id, users_to_approver, approver_id_vals, required, sequence):
        # if user_id not in users_to_approver.keys():
        approver_id_vals.append(Command.create({
            'user_id': user_id,
            'status': 'new',
            'required': required,
            'sequence': sequence,
        }))

    @api.constrains('approver_ids')
    def _check_approver_ids(self):
        for request in self:
            # make sure the approver_ids are unique per request
            if len(request.approver_ids) != len(request.approver_ids.user_id):
                raise UserError(_("You cannot assign the same approver multiple times on the same request."))

    @api.depends('category_id', 'request_owner_id')
    def _compute_approver_ids(self):
        for request in self:
            print(f"request.demand_product_line_ids 1: {request.demand_product_line_ids}")
            request.approver_ids = [(5, 0, 0)]
            users_to_approver = {}
            for approver in request.approver_ids:
                users_to_approver[approver.user_id.id] = approver

            users_to_category_approver = {}
            for approver in request.category_id.approver_ids:
                users_to_category_approver[approver.user_id.id] = approver

            approver_id_vals = []

            if request.category_id.manager_approval:
                employee = self.env['hr.employee'].search([('user_id', '=', request.request_owner_id.id)], limit=1)
                if employee.parent_id.user_id:
                    manager_user_id = employee.parent_id.user_id.id
                    manager_required = request.category_id.manager_approval == 'required'
                    # We set the manager sequence to be lower than all others (9) so they are the first to approve.
                    self._create_or_update_approver(manager_user_id, users_to_approver, approver_id_vals, manager_required, 6)
                    
                    # add manager manager
                    if employee.parent_id.parent_id and request.category_id.manager_manager_approval == True:
                        manager_manager_user_id = employee.parent_id.parent_id.user_id.id
                        print(f"manager_manager_user_id: {manager_manager_user_id}, {employee.parent_id.parent_id.user_id.name}")
                        self._create_or_update_approver(manager_manager_user_id, users_to_approver, approver_id_vals, manager_required, 7)
                    # end add manager manager

                    # add manager manager manager
                    if employee.parent_id.parent_id.parent_id and request.category_id.manager_manager_manager_approval == True:
                        manager_manager_manager_user_id = employee.parent_id.parent_id.parent_id.user_id.id
                        print(f"manager_manager_manager_user_id: {manager_manager_manager_user_id}, {employee.parent_id.parent_id.parent_id.user_id.name}")
                        self._create_or_update_approver(manager_manager_manager_user_id, users_to_approver, approver_id_vals, manager_required, 8)
                    # end add manager manager manager


                    if manager_user_id in users_to_category_approver.keys():
                        users_to_category_approver.pop(manager_user_id)

            # add Manger Header if exist assets
            print(f"request.demand_product_line_ids 2: {request.demand_product_line_ids}")
            has_fixed_asset = False
            for line in request.demand_product_line_ids:
                if line.demand_product_id.type == "2":  # Fixed Asset
                    has_fixed_asset = True
                    break

            if has_fixed_asset:
                # نجيب الموظف صاحب الطلب
                employee = self.env['hr.employee'].search([('user_id', '=', request.request_owner_id.id)], limit=1)
                if employee:
                    ceo = employee
                    # نعمل loop لغاية ما نوصل للمدير اللي ما عنده parent_id
                    while ceo.parent_id:
                        ceo = ceo.parent_id

                    if ceo.user_id:
                        ceo_user_id = ceo.user_id.id
                        print(f"CEO detected: {ceo_user_id}, {ceo.user_id.name}")
                        # نضيف المدير التنفيذي للمعتمدين في sequence = 9
                        self._create_or_update_approver(
                            ceo_user_id,
                            users_to_approver,
                            approver_id_vals,
                            False,  # نفس required اللي جاي من منطق المدير
                            9,
                        )
            # end add Manger Header if exist assets

            for user_id in users_to_category_approver:
                self._create_or_update_approver(user_id, users_to_approver, approver_id_vals,
                                                users_to_category_approver[user_id].required,
                                                users_to_category_approver[user_id].sequence)

            # remove duplicate approver_id_vals
            # remove duplicate approver_id_vals (keeping the last occurrence)
            unique_user_ids = set()
            filtered_approver_id_vals = []
            for approver_data in reversed(approver_id_vals): # لاحظ هنا عكسنا الترتيب
                user_id = approver_data[2]['user_id']  # نأخذ user_id من الدكتشنري
                if user_id not in unique_user_ids:
                    unique_user_ids.add(user_id)
                    filtered_approver_id_vals.append(approver_data)

            # الآن نعكس النتيجة حتى ترجع بالترتيب الطبيعي
            filtered_approver_id_vals.reverse()
            approver_id_vals = filtered_approver_id_vals
            # end remove duplicate approver_id_vals

            request.update({'approver_ids': approver_id_vals})

    @api.onchange( 'demand_product_line_ids')
    def _onchange_demand_product_line_ids(self):
        for request in self:
            
            print(f"_onchange_demand_product_line_ids 1: {request.demand_product_line_ids}")
            if any(line.state != 'new' for line in request.demand_product_line_ids):
                continue

            
            
            request.approver_ids = [(5, 0, 0)]
            users_to_approver = {}
            for approver in request.approver_ids:
                users_to_approver[approver.user_id.id] = approver

            users_to_category_approver = {}
            for approver in request.category_id.approver_ids:
                users_to_category_approver[approver.user_id.id] = approver

            approver_id_vals = []

            if request.category_id.manager_approval:
                employee = self.env['hr.employee'].search([('user_id', '=', request.request_owner_id.id)], limit=1)
                if employee.parent_id.user_id:
                    manager_user_id = employee.parent_id.user_id.id
                    manager_required = request.category_id.manager_approval == 'required'
                    # We set the manager sequence to be lower than all others (9) so they are the first to approve.
                    self._create_or_update_approver(manager_user_id, users_to_approver, approver_id_vals, manager_required, 6)
                    
                    # add manager manager
                    if employee.parent_id.parent_id and request.category_id.manager_manager_approval == True:
                        manager_manager_user_id = employee.parent_id.parent_id.user_id.id
                        print(f"manager_manager_user_id: {manager_manager_user_id}, {employee.parent_id.parent_id.user_id.name}")
                        self._create_or_update_approver(manager_manager_user_id, users_to_approver, approver_id_vals, manager_required, 7)
                    # end add manager manager

                    # add manager manager manager
                    if employee.parent_id.parent_id.parent_id and request.category_id.manager_manager_manager_approval == True:
                        manager_manager_manager_user_id = employee.parent_id.parent_id.parent_id.user_id.id
                        print(f"manager_manager_manager_user_id: {manager_manager_manager_user_id}, {employee.parent_id.parent_id.parent_id.user_id.name}")
                        self._create_or_update_approver(manager_manager_manager_user_id, users_to_approver, approver_id_vals, manager_required, 8)
                    # end add manager manager manager


                    if manager_user_id in users_to_category_approver.keys():
                        users_to_category_approver.pop(manager_user_id)

            # add Manger Header if exist assets
            print(f"request.demand_product_line_ids 2: {request.demand_product_line_ids}")
            has_fixed_asset = False
            for line in request.demand_product_line_ids:
                if line.demand_product_id.type == "2":  # Fixed Asset
                    has_fixed_asset = True
                    break

            if has_fixed_asset:
                # نجيب الموظف صاحب الطلب
                employee = self.env['hr.employee'].search([('user_id', '=', request.request_owner_id.id)], limit=1)
                if employee:
                    ceo = employee
                    # نعمل loop لغاية ما نوصل للمدير اللي ما عنده parent_id
                    while ceo.parent_id:
                        ceo = ceo.parent_id

                    if ceo.user_id:
                        ceo_user_id = ceo.user_id.id
                        print(f"CEO detected: {ceo_user_id}, {ceo.user_id.name}")
                        # نضيف المدير التنفيذي للمعتمدين في sequence = 9
                        self._create_or_update_approver(
                            ceo_user_id,
                            users_to_approver,
                            approver_id_vals,
                            False,  # نفس required اللي جاي من منطق المدير
                            9,
                        )
            # end add Manger Header if exist assets

            for user_id in users_to_category_approver:
                self._create_or_update_approver(user_id, users_to_approver, approver_id_vals,
                                                users_to_category_approver[user_id].required,
                                                users_to_category_approver[user_id].sequence)

            # remove duplicate approver_id_vals
            # remove duplicate approver_id_vals (keeping the last occurrence)
            unique_user_ids = set()
            filtered_approver_id_vals = []
            for approver_data in reversed(approver_id_vals): # لاحظ هنا عكسنا الترتيب
                user_id = approver_data[2]['user_id']  # نأخذ user_id من الدكتشنري
                if user_id not in unique_user_ids:
                    unique_user_ids.add(user_id)
                    filtered_approver_id_vals.append(approver_data)

            # الآن نعكس النتيجة حتى ترجع بالترتيب الطبيعي
            filtered_approver_id_vals.reverse()
            approver_id_vals = filtered_approver_id_vals
            # end remove duplicate approver_id_vals

            request.update({'approver_ids': approver_id_vals})



    @api.depends('name', 'category_id.name', 'statement_subject')
    def _compute_display_name(self):
        for rec in self:
            if rec.statement_subject:
                rec.display_name = f"{rec.category_id.name} {rec.statement_subject} - [{rec.name}]"
            else:
                rec.display_name = f"{rec.category_id.name} - [{rec.name}]"
    
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None, order=None):
        args = args or []
        domain = ['|', '|', ('name', operator, name), ('statement_subject', operator, name), ('category_id.name', operator, name)]
        records = self._search(domain + args, limit=limit, order=order)
        return records
    
    pending_user_id = fields.Many2one(
        'res.users', 
        string="Pending User",
        compute="_compute_pending_user",
        store=True
    )
    
    @api.depends('approver_ids', 'approver_ids.status')
    def _compute_pending_user(self):
        for rec in self:
            if rec.approver_ids:
                for approver in rec.approver_ids:
                    if approver.status == 'pending':
                        rec.pending_user_id = approver.user_id
                        break
                    else:
                        rec.pending_user_id = False
            else:
                rec.pending_user_id = False
                
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id,
        tracking=True
    )
                

    total_all = fields.Float(
        compute='_compute_total_all', 
        default=0.0,
        string='Total Cost All', 
        readonly=True, 
        store=True,
    )
    total_all_txt = fields.Char(
        compute='_compute_total_all', 
        string='Total Cost All Text', 
        readonly=True, 
        store=False,
    )
    
    @api.depends('demand_product_line_ids.total')
    def _compute_total_all(self):
        for record in self:
            total_all = 0.0
            for line in record.demand_product_line_ids:
                total_all = total_all + line.total
            record.total_all = total_all  # ← حفظ الناتج في الحقل
            currency = record.currency_id.symbol
            record.total_all_txt = record.amount_to_text_arabic(total_all, currency)

    def amount_to_text_arabic(self, number, currency):
        number = abs(number)
        arabic_digits = [
            "صفر", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة"
        ]
        arabic_tens = [
            "", "عشرة", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"
        ]
        arabic_teens = [
            "عشرة", "إحدى عشر", "إثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر",
            "ستة عشر", "سبعة عشر", "ثمانية عشر", "تسعة عشر"
        ]
        arabic_hundreds = [
            "", "مائة", "مائتين", "ثلاثمائة", "أربعمائة", "خمسمائة", "ستمائة", "سبعمائة", "ثمانمائة", "تسعمائة"
        ]
        arabic_large_units = [
            "", "ألف", "مليون", "مليار", "تريليون", "كوادرليون", "كوادريليون"
        ]

        def to_arabic_word(n):
            if n < 10:
                return arabic_digits[n]
            elif n < 20:
                return arabic_teens[n - 10]
            elif n < 100:
                tens = n // 10
                ones = n % 10
                if ones == 0:
                    return arabic_tens[tens]
                else:
                    return arabic_digits[ones] + " و " + arabic_tens[tens]
            elif n < 1000:
                hundreds = n // 100
                remainder = n % 100
                if remainder == 0:
                    return arabic_hundreds[hundreds]
                else:
                    return arabic_hundreds[hundreds] + " و " + to_arabic_word(remainder)
            else:
                return ""

        def convert_large_number(n):
            if n == 0:
                return arabic_digits[0]

            parts = []
            unit_index = 0

            while n > 0:
                group = n % 1000
                if group > 0:
                    group_text = to_arabic_word(group)
                    if arabic_large_units[unit_index]:
                        group_text += " " + arabic_large_units[unit_index]
                    parts.append(group_text)
                n //= 1000
                unit_index += 1

            return " و ".join(reversed(parts))

        integer_part = int(number)
        integer_text = convert_large_number(integer_part)

        decimal_part = number - integer_part
        if decimal_part > 0:
            decimal_part = round(decimal_part * 100)
            decimal_text = convert_large_number(decimal_part)
            return _("ففط {} {} و {} فلس لاغير").format(integer_text, currency, decimal_text)
        else:
            return _("فقط {} {} لاغير").format(integer_text, currency)
        
    def action_reject(self):
        print("action_reject approval_request: action_reject approval_request")
        action = self.env['ir.actions.actions']._for_xml_id('mhma_inventory.approval_rejection_reason_action')
        action['context'] = {'default_approval_request_id': self.id}
        # super().action_refuse()
        return action
    
    def action_approve(self):
        print("action_approve approval_request: action_approve approval_request")
        super().action_approve()
        if (self.env.user.lang == 'ar_001'):
            self.message_post(
                body=f"تمت الموافقة",  # نص الرسالة
                message_type='comment',  # نوع الرسالة (تعليق/رسالة)
                # subtype_xmlid='mail.mt_comment',  # هذا يضمن إرسالها للمتابعين
                partner_ids=[self.request_owner_id.partner_id.id]
            )
        else:
            self.message_post(
                body=f"Approved",  # نص الرسالة
                message_type='comment',  # نوع الرسالة (تعليق/رسالة)
                # subtype_xmlid='mail.mt_comment',  # هذا يضمن إرسالها للمتابعين
                partner_ids=[self.request_owner_id.partner_id.id]
            )
            
    def action_confirm(self):
        if(self.aprvl_type == "0" 
            or self.aprvl_type == "1" 
            or self.aprvl_type == "2" 
            or self.aprvl_type == "3" 
            or self.aprvl_type == "4" 
            or self.aprvl_type == "5" 
            or self.aprvl_type == "6"):
            if not self.demand_product_line_ids:
                raise UserError(_("Please add demand product lines"))
            if self.demand_product_line_ids:
                for line in self.demand_product_line_ids:
                    if line.qty <= 0:
                        raise UserError(_("Quantity must be greater than zero"))
        super().action_confirm()
        
    @api.onchange('category_id')
    def _onchange_category(self):
        print("_onchange_category approval_request: _onchange_category approval_request")
        for rec in self:
            activities = rec.activity_ids
            if rec.env.user.lang == 'ar_001':
                activities.action_feedback(
                    feedback=_(f"سيتم اعادة الارسال بسبب تغيير الفئة"),
                )
            else:
                activities.action_feedback(
                    feedback=_(f"The request will be resubmitted due to category change"),
                )


    # Request Add Partner
    partner_ids = fields.One2many(
        comodel_name = 'res.partner', 
        inverse_name = 'approval_request_id',
        string = 'Partners',
    )
    len_partner_ids = fields.Integer(
        string='Number of Partners',
        compute='_compute_len_partner_ids',
        store=True,
        default=0
    )
    @api.depends('partner_ids')
    def _compute_len_partner_ids(self):
        for rec in self:
            rec.len_partner_ids = len(rec.partner_ids)
    
    partner_name = fields.Char(string="Name", tracking=True)
    partner_address = fields.Char(string="Address", tracking=True)
    partner_email = fields.Char(string="Email", tracking=True)
    partner_phone = fields.Char(string="Phone", tracking=True)
    partner_mobile = fields.Char(string="Mobile", tracking=True)
    partner_debit_account_id = fields.Many2one(
        'account.account', 
        string="Debit Account",
        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False)]",
        tracking=True,
    )
    partner_credit_account_id = fields.Many2one(
        'account.account', 
        string="Credit Account",
        domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False)]",
        tracking=True,
    )
    
    def action_add_vendor(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Vendor'),
            'res_model': 'res.partner',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_partner_type': 'vendor',
                'default_is_company': True,
                'default_category_id':  [],
                'default_approval_request_id': self.id,
            }
        }
    def action_add_customer(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Customer'),
            'res_model': 'res.partner',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_partner_type': 'customer',
                'default_is_company': True,
                'default_category_id':  [],
                'default_approval_request_id': self.id,
            }
        }
    def action_add_partner(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Partner'),
            'res_model': 'res.partner',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_partner_type': 'never',
                'default_is_company': False,
                'default_approval_request_id': self.id,
            }
        }

    # HR Expense
    approval_request_need_ids = fields.One2many(
        comodel_name = 'hr.expense', 
        inverse_name = 'approval_request_need_id',
        string = 'Direct Purchases(Expenses)',
    )

    approval_direct_purchase_ids = fields.One2many(
        comodel_name = 'hr.expense', 
        inverse_name = 'approval_direct_purchase_id',
        string = 'Direct Purchases(Expenses) per Directive',
    )
