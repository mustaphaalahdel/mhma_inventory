from odoo import _, models, fields, api
from odoo.exceptions import UserError, ValidationError
import re
from datetime import date, timedelta
from lxml import etree

class StockPicking(models.Model):
    _inherit = ['stock.picking',]

    active = fields.Boolean(default=True, tracking=True)

    statement_subject = fields.Char(string='Statement Subject', tracking=True)

    date_done = fields.Datetime('Date of Transfer', tracking=True, copy=False, readonly=False, help="Date at which the transfer has been processed or cancelled.")
    depart_id = fields.Many2one(comodel_name="hr.department", string='Department', store=True, compute='_compute_depart_id', readonly=0, copy=True)
    partner_user_id = fields.Many2one('res.users', readonly=False, store=True, compute='_compute_depart_id', copy=True)
    is_send_to_recipient = fields.Boolean()
    
    total_cost_all = fields.Float(
        compute='_compute_total_cost_all', 
        default=0.0,
        string='Total Cost All', 
        readonly=True, 
        store=True,
    )
    total_cost_all_txt = fields.Char(
        compute='_compute_total_cost_all', 
        string='Total Cost All Text', 
        readonly=True, 
        store=False,
    )
    @api.depends('move_ids.total_stock_move')
    def _compute_total_cost_all(self):
        for record in self:
            total_cost_all = 0.0
            for move in record.move_ids:
                total_cost_all = total_cost_all + move.total_stock_move
            record.total_cost_all = total_cost_all  # ← حفظ الناتج في الحقل
            record.total_cost_all_txt = record.amount_to_text_arabic(total_cost_all)
            
    # default_currency_id = fields.Many2one(
    #     'res.currency', 
    #     string='Currency', 
    #     related='company_id.currency_id',
    #     # default=lambda self: self.env.company.currency_id,
    # )
    
    def button_send_to_recipient(self):
        # if self.approval_id and self.state in ['assigned', 'done']:
        if self.partner_user_id:
            print(f"self.partner_user_id.partner_id: {self.partner_user_id.partner_id}")
            if (self.env.user.lang == 'ar_001'):
                # self.message_post(
                #     body=_(f"من المخزون إلى {self.partner_user_id.name}، يُرجى تأكيد الصرف عند الاستلام."),  # نص الرسالة
                #     message_type='comment',  # نوع الرسالة (تعليق/رسالة)
                #     partner_ids=[self.partner_user_id.partner_id.id]
                #     # subtype_xmlid="mail.mt_comment",  # هذا يضمن إرسالها للمتابعين
                #     # notification_ids=notification_ids,
                #     # partner_ids=[self.approval_id.request_owner_id.partner_id.id, self.partner_user_id.partner_id.id]  # إرسالها لمتابع معين فقط
                # )
                self.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    user_id=self.partner_user_id.id,
                    summary="قم بتأكيد الصرف عند الاستلام",
                    note=_(f"من المخزون إلى {self.partner_user_id.name}، يُرجى تأكيد الصرف عند الاستلام."),
                    date_deadline=date.today()
                )
            else:
                # self.message_post(
                #     body=_(f"From stock to {self.partner_user_id.name}, confirm the disbursement upon receipt."),  # نص الرسالة
                #     message_type='comment',  # نوع الرسالة (تعليق/رسالة)
                #     subtype_xmlid="mail.mt_comment",  # هذا يضمن إرسالها للمتابعين
                #     # notification_ids=notification_ids,
                #     # partner_ids=[self.approval_id.request_owner_id.partner_id.id, self.partner_user_id.partner_id.id]  # إرسالها لمتابع معين فقط
                # )
                self.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    user_id=self.partner_user_id.id,
                    summary="Confirm the disbursement upon receipt",
                    note=_(f"From stock to {self.partner_user_id.name}, confirm the disbursement upon receipt."),
                    date_deadline=date.today()
                )
            self.is_send_to_recipient = True
            

    # name = fields.Char(
    #     'Reference', default='/',
    #     copy=False, index='trigram', readonly=False)

    # لحساب الكمية المتوفرة في موقع مخزون محدد لكل حركة مخزونية عند الانتقاء
    # my_quant = fields.Integer(compute='_compute_my_test', string='My Quant')
    # @api.onchange('move_ids_without_package')
    # def _compute_my_test(self):
    #     for picking in self:
    #         if picking.move_ids_without_package:
    #             for move in picking.move_ids_without_package:
    #                 print(f"location: {picking.location_id.name} - product: {move.product_id.name}")
    #                 quants = self.env['stock.quant'].search(
    #                     [
    #                         ('product_id', '=', move.product_id.id), 
    #                         ('location_id', 'child_of', picking.location_id.id),
    #                         ("location_id.usage", "in", ["internal", "view"])
    #                     ])
    #                 q = 0
    #                 for quant in quants:
    #                     print(f"quant: {quant.inventory_quantity_auto_apply} - product: {quant.product_id.name} - location: {quant.location_id.name}")
    #                     q += quant.inventory_quantity_auto_apply
    #                 print(f"stock.quant to product move: {q}")
    

    @api.depends('partner_id', 'products_availability')
    def _compute_depart_id(self):
        for picking in self:
            if picking.partner_id.employee_ids:    
                picking.depart_id = picking.partner_id.employee_ids[0].department_id
            if picking.partner_id.user_ids:
                picking.partner_user_id = picking.partner_id.user_ids[0]

    approval_id = fields.Many2one(
        comodel_name="approval.request",
        readonly=False,
        store=True,
        compute="_set_approval_disbursing_directive_id",
        domain=[('aprvl_type', '=', '0'), ('request_status', 'in', ['approved', 'pending'])],
    )
    approval_disbursing_directive_id = fields.Many2one(
        comodel_name="approval.request",
        domain=[('aprvl_type', '=', '4'), ('request_status', '=', 'approved')],
    )

    @api.depends('approval_disbursing_directive_id')
    def _set_approval_disbursing_directive_id(self):
        for picking in self:
            if picking.approval_disbursing_directive_id:
                if picking.approval_disbursing_directive_id.dsbrs_id:
                    picking.approval_id = picking.approval_disbursing_directive_id.dsbrs_id

    @api.onchange('approval_id')
    def _set_to_note(self):
        for picking in self:
            if picking.approval_id:
                picking.origin = picking.approval_id.name
                picking.partner_id = picking.approval_id.request_owner_id.partner_id
            else:
                picking.origin = False
                picking.partner_id = False
                picking.depart_id = False
                picking.partner_user_id = False


    scheduled_date = fields.Datetime(
        'Scheduled Date', compute='_compute_scheduled_date', inverse='_set_scheduled_date', store=True,
        index=True, default=fields.Datetime.now, tracking=True,
        states={'done': [('readonly', False)], 'cancel': [('readonly', False)]},
        help="Scheduled time for the first part of the shipment to be processed. Setting manually a value here would set it as expected date for all the stock moves.",
    )

    def _set_scheduled_date(self):
        for picking in self:
            picking.move_line_ids.write({'date': picking.scheduled_date})


    def action_stock_picking(self):
        return self.env.ref('mhma_inventory.action_report_picking').report_action(self)

    is_req_revieve = fields.Boolean("Has the stock disbursement been received?")
    def button_approve(self):
        activities = self.sudo().activity_ids.filtered(lambda act: act.user_id == self.env.user)
        if (self.env.user.lang == 'ar_001'):
            # self.sudo().message_post(
            #     body="تم استلام الصرف المخزني",  # نص الرسالة
            #     message_type='comment',  # نوع الرسالة (تعليق/رسالة)
            #     subtype_xmlid='mail.mt_comment',  # هذا يضمن إرسالها للمتابعين
            # )
            activities.action_feedback(
                feedback=_(f"تم استلام الصرف المخزني"),
            )
        else:
            # self.sudo().message_post(
            #     body="Stock disbursement has been received.",  # نص الرسالة
            #     message_type='comment',  # نوع الرسالة (تعليق/رسالة)
            #     subtype_xmlid='mail.mt_comment',  # هذا يضمن إرسالها للمتابعين
            # )
            activities.action_feedback(
                feedback=_(f"Stock disbursement has been received."),
            )
        self.sudo().is_req_revieve = True
        if (self.env.user.lang == 'ar_001'):
            self.sudo().note = f"""{self.sudo().note}<p>{self.env.user.name} اكد بتاريخ {fields.Datetime.now()}</p>"""
        else:
            self.sudo().note = f"""{self.sudo().note}<p>{self.env.user.name} confirmed In Date {fields.Datetime.now()}</p>"""
            
            
            
            
    def amount_to_text_arabic(self, number):
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
            return _("ففط {} ريال يمني و {} فلس لاغير").format(integer_text, decimal_text)
        else:
            return _("فقط {} ريال يمني لاغير").format(integer_text)
        
        
    purchase_order_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Purchase Order',
        readonly=True,
    )
    
    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.group_id:
                purchase_order = self.env['purchase.order'].search(
                    [('name', '=', rec.group_id.name)],
                    limit=1
                )
                # تجنب التكرار: لا تكتب إذا كانت القيمة نفسها
                if rec.purchase_order_id != purchase_order:
                    rec.with_context(skip_write=True).purchase_order_id = purchase_order
        return res

    # override button_validate
    def button_validate(self):
        for rec in self:
            if rec.partner_user_id and not rec.is_req_revieve:
                raise ValidationError(_("Receipt must be confirmed before approval."))

        # seq stock picking
        res = super(
                StockPicking, self.with_context(keep_line_sequence=True)
            ).button_validate()

        for rec in self:
            if rec.purchase_order_id:
                purchase_order = rec.purchase_order_id.sudo()
                date_deadline = date.today() + timedelta(days=1)

                if self.env.user.lang and self.env.user.lang.startswith('ar'):
                    purchase_order.activity_schedule(
                        act_type_xmlid='mail.mail_activity_data_todo',
                        user_id=purchase_order.create_uid.id,  # أو self.env.user.id إذا تبيه للمستخدم الحالي
                        summary=_("قم بانشاء فاتور شراء"),
                        note=_(f"تم توريد امر الشراء {purchase_order.name}، مرجع التوريد {rec.name}، قم بانشاء فاتورة"),  # الوصف التفصيلي
                        date_deadline=date_deadline
                    )
                else:
                    purchase_order.activity_schedule(
                        act_type_xmlid='mail.mail_activity_data_todo',
                        user_id=purchase_order.create_uid.id,
                        summary=_("Create a Bill"),
                        note=_(f"Order {purchase_order.name}, reference {rec.name}, create an Bill"),  # الوصف التفصيلي
                        date_deadline=date_deadline
                    )
        return res


    # seq stock picking
    @api.depends("move_ids_without_package")
    def _compute_max_line_sequence(self):
        """Allow to know the highest sequence entered in move lines.
        Then we add 1 to this value for the next sequence, this value is
        passed to the context of the o2m field in the view.
        So when we create new move line, the sequence is automatically
        incremented by 1. (max_sequence + 1)
        """
        for picking in self:
            picking.max_line_sequence = (
                max(picking.mapped("move_ids_without_package.sequence") or [0]) + 1
            )

    max_line_sequence = fields.Integer(
        string="Max sequence in lines", compute="_compute_max_line_sequence"
    )

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.move_ids_without_package:
                # Check if the record ID is an integer (real ID)
                # or a string (virtual ID)
                if isinstance(line.id, int):
                    line.sequence = current_sequence
                    current_sequence += 1

    def copy(self, default=None):
        return super(StockPicking, self.with_context(keep_line_sequence=True)).copy(
            default
        )

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        """Append the default sequence.

        The context of `move_ids_without_package` is already overloaded
        and replacing it in a view does not scale across other extension
        modules.
        """
        res = super().get_view(view_id=view_id, view_type=view_type, **options)

        if res.get("arch") and view_type == "form":
            doc = etree.XML(res["arch"])
            elements = doc.xpath("//field[@name='move_ids_without_package']")
            if elements:
                element = elements[0]
                context = element.get("context", "{}")
                context = "{}{}, {}".format(
                    context[0], "'default_sequence': max_line_sequence", context[1:]
                )
                element.set("context", context)
            res["arch"] = etree.tostring(doc, encoding="unicode")
        return res

