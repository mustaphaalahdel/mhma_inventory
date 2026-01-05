from odoo import fields, models, api, _

class ProductProduct(models.Model):
    _inherit = "product.product"

    display_name = fields.Char(
        automatic=True,
        compute="_compute_display_name",
        search="_search_display_name",
    )
    
    qty_from_valuation = fields.Float(
        string='Quantity From Valuation', 
        compute='_compute_qty_and_cost_from_valuation',
        store=True,
        readonly=True,
    )
    # cost_time_qty_consu = fields.Float(
    #     string='Cost Time Qty', 
    #     compute='_compute_qty_and_cost_from_valuation',
    #     store=True,
    #     readonly=True,
    # )

    @api.depends('stock_valuation_layer_ids')
    def _compute_qty_and_cost_from_valuation(self):
        for rec in self:
            rec.qty_from_valuation = sum(rec.stock_valuation_layer_ids.mapped('quantity'))
            # rec.cost_time_qty_consu = rec.qty_from_valuation * rec.standard_price
            
    def action_valuatin_report(self):
        return {
            'name': 'Valuation Report',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'view_id': self.env.ref('mhma_inventory.stock_valuation_layer_tree_simple').id,
            'res_model': 'stock.valuation.layer',
            'target': 'current',
            'domain': [('product_id', 'in', self.ids)],
        }

    # full_name = fields.Char(
    #     compute='_compute_full_name',
    #     store=True,
    #     readonly=False,
    # )
    # @api.depends('display_name')
    # def _compute_full_name(self):
    #     for rec in self:
    #         rec.full_name = rec.display_name


    product_template_variant_value_ids = fields.Many2many('product.template.attribute.value', relation='product_variant_combination',
                                                        domain=[('attribute_line_id.value_count', '>', 0)], string="Variant Values", ondelete='restrict')

    product_variant_descc = fields.Html(
        required=False,
        translate=True,
        string="Product Variant Desc",
    )

    def _search_display_name(self, operator, value):
        recs = (
            self.with_context(active_test=False)
            .search([])
            .filtered_domain([("display_name", operator, value)])
        )
        return [("id", "in", recs.ids)]

    cost_time_qty = fields.Float(string='Cost Time Qty', compute='_compute_cost_time_qty')
    

    @api.depends('standard_price', 'qty_available')
    def _compute_cost_time_qty(self):
        for rec in self:
            rec.cost_time_qty = rec.standard_price * rec.qty_available


    def _get_category_symbol_sequence(self, category):
        symbols = []
        while category:
            if category.symbol:
                symbols.append(category.symbol)
            category = category.parent_id
        symbols.reverse()
        return "-".join(symbols)

    @api.model
    def create(self, vals):
        recs = super().create(vals)

        # معالجة default_code لكل سجل جديد
        for rec in recs:
            if not rec.default_code:
                get_category_symbol_sequence = rec._get_category_symbol_sequence(rec.categ_id)

                # جلب كل المنتجات في نفس الفئة مرتبة
                products = self.env['product.product'].search(
                    [('categ_id', '=', rec.categ_id.id)], order='id'
                )

                # إنشاء dict لترتيب المنتجات
                product_rank = {prod.id: idx + 1 for idx, prod in enumerate(products)}

                # تعيين default_code باستخدام write مع skip_product_write
                rec.with_context(skip_product_write=True).write({
                    'default_code': f"{get_category_symbol_sequence}-{str(product_rank[rec.id]).zfill(5)}"
                })

        return recs
        
    def write(self, vals):
        # لو جاي من مكان فيه skip، تجاوز المنطق المخصص
        if self.env.context.get('skip_product_write'):
            return super().write(vals)

        # نخزّن القيم القديمة للفئة
        old_categ_map = {rec.id: rec.categ_id.id for rec in self}

        # نعمل التحديث الأصلي
        res = super().write(vals)

        # بعد التحديث نتحقق من التغيير أو غياب الكود
        for rec in self:
            old_categ_id = old_categ_map.get(rec.id)
            new_categ_id = rec.categ_id.id

            if not rec.default_code or old_categ_id != new_categ_id:
                # احصل على رمز الفئة
                get_category_symbol_sequence = rec._get_category_symbol_sequence(rec.categ_id)

                # كل المنتجات في الفئة الجديدة
                products = self.env['product.product'].search(
                    [('categ_id', '=', new_categ_id)], order='id'
                )

                # إعادة الترتيب وإعطاء الأكواد
                for idx, product in enumerate(products, start=1):
                    product.with_context(skip_product_write=True).write({
                        'default_code': f"{get_category_symbol_sequence}-{str(idx).zfill(5)}"
                    })

        return res

                

    inventory_unit = fields.Char(
        string='Inventory Unit', 
        compute='_compute_inventory_unit',
        store=True,
        readonly=False,
    )

    @api.depends('uom_id.name')
    def _compute_inventory_unit(self):
        for rec in self:
            rec.inventory_unit = rec.uom_id.name

    @api.depends('inventory_unit', 'country_of_origin')
    def _compute_display_name(self):
        super(ProductProduct, self)._compute_display_name()
        for rec in self:
            if rec.country_of_origin:
                if (rec.env.user.lang == 'ar_001'):
                    rec.display_name = _(f"{rec.display_name} صنع في {rec.country_of_origin.name}")
                else:
                    rec.display_name = _(f"{rec.display_name} made in {rec.country_of_origin.name}")
            if rec.inventory_unit:
                rec.display_name = f"{rec.display_name} [{rec.inventory_unit}]"

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None, order=None):
        args = args or []
        domain = [
            '|', '|', '|',
            ('display_name', operator, name),
            ('barcode', operator, name),
            ('product_tag_ids.name', operator, name),
            ('additional_product_tag_ids.name', operator, name),
        ]
        return self._search(domain + args, limit=limit, order=order, access_rights_uid=name_get_uid)
    