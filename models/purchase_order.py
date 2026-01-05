from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approval_purchase_specifications_id = fields.Many2one(
        comodel_name='approval.request', 
        string="Purchase Specifications",
        domain="[('aprvl_type', '=', '2'), ('request_status', '=', 'approved')]",
    )

    approval_purchase_request_id = fields.Many2one(
        comodel_name='approval.request', 
        domain="[('request_status', '=', 'approved'), '|', ('aprvl_type', '=', '1'), ('aprvl_type', '=', '3')]"
    )
    
    request_ref_id = fields.Many2one(
        comodel_name='approval.request',
        compute="_compute_request_ref",
        store=True,
    )
    
    
    def _prepare_demand_lines(self, lines):
        """Helper to map demand_product_line_ids into One2many commands"""
        self.demand_product_line_ids  = [(5, 0, 0)]
        return [
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
            }) for line in lines
        ]
    
    @api.depends('approval_purchase_specifications_id', 'approval_purchase_request_id')
    def _compute_request_ref(self):
        for rec in self:
            
            # rec.request_ref_id = False
            # rec.approval_purchase_request_id = False
            # rec.approval_purchase_specifications_id = False
            # rec.demand_product_line_ids  = [(5, 0, 0)]

            # rec.partner_id = False


            if rec.approval_purchase_specifications_id:
                rec.request_ref_id = False
                # rec.partner_id = rec.approval_purchase_specifications_id.partner_id
                rec.notes = rec.approval_purchase_specifications_id.determine_specifications
                rec.approval_purchase_request_id = rec.approval_purchase_specifications_id.req_purchase_id
                if rec.approval_purchase_specifications_id.req_purchase_id:
                    rec.request_ref_id = rec.approval_purchase_specifications_id.req_purchase_id.dsbrs_id
                rec.demand_product_line_ids = rec._prepare_demand_lines(
                    rec.approval_purchase_specifications_id.demand_product_line_ids
                )
            elif rec.approval_purchase_request_id and not rec.approval_purchase_specifications_id:
                # rec.partner_id = rec.approval_purchase_request_id.partner_id
                rec.notes = rec.approval_purchase_request_id.reason
                rec.request_ref_id = rec.approval_purchase_request_id.dsbrs_id
                rec.demand_product_line_ids = rec._prepare_demand_lines(
                    rec.approval_purchase_request_id.demand_product_line_ids
                )
            elif rec.request_ref_id and not rec.approval_purchase_request_id and not rec.approval_purchase_specifications_id:
                # rec.request_ref_id is empty null
                rec.request_ref_id = False

    # @api.onchange('approval_purchase_specifications_id')
    # def _set_notes(self):
    #     for rec in self:
    #         rec.request_ref_id = False
    #         rec.approval_purchase_request_id = False
    #         rec.demand_product_line_ids  = [(5, 0, 0)]
    #         if rec.approval_purchase_specifications_id:
    #             rec.notes = rec.approval_purchase_specifications_id.determine_specifications
    #             rec.origin = rec.approval_purchase_specifications_id.name
    #             rec.demand_product_line_ids = [
    #                     (0, 0, {
    #                         'demand_product_id': line.demand_product_id.id,
    #                         'qty': line.modified_qty,
    #                         'uom_id': line.uom_id.id,
    #                         'desc': line.modified_desc,
    #                         'detail': line.modified_detail,
    #                         'estimate_cost': line.modified_estimate_cost,
    #                         'modified_desc': line.modified_desc,
    #                         'modified_qty': line.modified_qty,
    #                         'modified_estimate_cost': line.modified_estimate_cost,
    #                         'modified_detail': line.modified_detail,
    #                         # أضف باقي الحقول التي تريد نسخها
    #                     }) for line in rec.approval_purchase_specifications_id.demand_product_line_ids
    #                 ]


    # @api.onchange('approval_purchase_request_id')
    # def _set_notes_2(self):
    #     for rec in self:
    #         rec.request_ref_id = False
    #         if not rec.approval_purchase_specifications_id:
    #             rec.demand_product_line_ids  = [(5, 0, 0)]
    #         if rec.approval_purchase_request_id:
    #             # rec.approval_purchase_specifications_id = False
    #             rec.notes = rec.approval_purchase_request_id.reason
    #             rec.origin = rec.approval_purchase_request_id.name
    #             rec.demand_product_line_ids  = [(5, 0, 0)]
    #             rec.demand_product_line_ids = [
    #                     (0, 0, {
    #                         'demand_product_id': line.demand_product_id.id,
    #                         'qty': line.modified_qty,
    #                         'uom_id': line.uom_id.id,
    #                         'desc': line.modified_desc,
    #                         'detail': line.modified_detail,
    #                         'estimate_cost': line.modified_estimate_cost,
    #                         'modified_desc': line.modified_desc,
    #                         'modified_qty': line.modified_qty,
    #                         'modified_estimate_cost': line.modified_estimate_cost,
    #                         'modified_detail': line.modified_detail,
    #                         # أضف باقي الحقول التي تريد نسخها
    #                     }) for line in rec.approval_purchase_request_id.demand_product_line_ids
    #                 ]


    # override action_create_invoice
    def action_create_invoice(self):
        for order in self:
            activities = order.activity_ids
            if order.env.user.lang == 'ar_001':
                activities.action_feedback(
                    feedback=_(f"تم انشاء فاتورة الشراء {order.name}"),
                )
            else:
                activities.action_feedback(
                    feedback=_(f"Purchase order bill has been created {order.name}"),
                )
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'purchase.order'),
                ('res_id', '=', order.id)
            ])
            if not attachments or not order.partner_ref :
                if order.env.user.lang == 'ar_001':
                    raise ValidationError(_(f'المرجع الخاص بالمورّد مطلوب، ويجب إرفاق فاتورة المورّد قبل إنشاء الفاتورة (يجب إرفاق الملفات في سجل الرسائل).'))
                else:
                    raise ValidationError(_(f'supplier reference is required and The supplier bill must be attached before creating an invoice (files must be attached in the message log).'))
        return super().action_create_invoice()
    

    supplier_id = fields.Many2one(
        'res.partner', 
        string='Supplier', 
        required=True, 
        change_default=True, 
        tracking=True, 
        check_company=True, 
        domain="[('partner_type', '=', 'vendor')]",
    )
    
    @api.onchange('partner_id')
    def _set_supplier_id(self):
        for rec in self:
            rec.supplier_id = rec.partner_id
            
    def _prepare_picking(self):
        print(f"_prepare_picking: _prepare_picking")
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.name,
                'partner_id': self.supplier_id.id
            })
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s", self.partner_id.name))
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.supplier_id.id,
            'purchase_order_id': self.id,
            'user_id': False,
            'date': self.date_order,
            'origin': self.name,
            'location_dest_id': self._get_destination_location(),
            'location_id': self.partner_id.property_stock_supplier.id,
            'company_id': self.company_id.id,
            'state': 'draft',
        }
        
    demand_product_line_ids = fields.One2many(
        comodel_name='mhma.demand.product.line', 
        inverse_name='purchase_order_id', 
        string='Demand Products',
    )
    
    confirmed_demand_product_lines = fields.Boolean(default=False, )
    
    rfq_total_all = fields.Float(
        compute='_compute_total_all', 
        default=0.0,
        string='Total Cost All', 
        readonly=True, 
        store=True,
    )
    rfq_total_all_txt = fields.Char(
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
            record.rfq_total_all = total_all  # ← حفظ الناتج في الحقل
            currency = record.currency_id.symbol
            record.rfq_total_all_txt = record.amount_to_text_arabic(total_all, currency)


            
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
        



    # to permission ___________________________________________________________________

    def _approval_allowed(self):
        """Returns whether the order qualifies to be approved by the current user"""
        self.ensure_one()
        return (
            self.company_id.po_double_validation == 'one_step'
            or (self.company_id.po_double_validation == 'two_step'
                and self.amount_total < self.env.company.currency_id._convert(
                    self.company_id.po_double_validation_amount, self.currency_id, self.company_id,
                    self.date_order or fields.Date.today()))
            or self.user_has_groups('purchase.group_purchase_manager,mhma_inventory.mhma_purchase_inventory_manager'))

