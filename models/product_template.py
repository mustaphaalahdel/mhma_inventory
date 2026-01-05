# Copyright 2023 Komit - Cuong Nguyen Mtm
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models,_,api
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

class ProductTemplate(models.Model):
    _inherit = "product.template"

    display_name = fields.Char(
        automatic=True,
        compute="_compute_display_name",
        search="_search_display_name",
    )

    product_dsbrs_type = fields.Selection(
        string="Product Disbursement Type",
        selection=[
            ("1", "Commodity product"),
            ("2", "Fixed Asset"),
            ("3", "Personal Custody"),
        ],
    )

    def _search_display_name(self, operator, value):
        recs = (
            self.with_context(active_test=False)
            .search([])
            .filtered_domain([("display_name", operator, value)])
        )
        return [("id", "in", recs.ids)]
    

    def _get_category_symbol_sequence(self, category):
        symbols = []
        while category:
            if category.symbol:
                symbols.append(category.symbol)
            category = category.parent_id
        symbols.reverse()
        return "-".join(symbols)
    
    def write(self, values):
        # خزن القيم القديمة للفئات
        old_categ_map = {rec.id: rec.categ_id.id for rec in self}

        res = super().write(values)

        for rec in self:
            old_categ_id = old_categ_map.get(rec.id)
            new_categ_id = rec.categ_id.id

            print(f"template old categ_id: {old_categ_id}, new categ_id: {new_categ_id}")

            # تحقق: إما ما عنده كود أو الفئة تغيّرت
            if not rec.default_code or old_categ_id != new_categ_id:
                get_category_symbol_sequence = rec._get_category_symbol_sequence(rec.categ_id)

                # احصل على المنتجات في الفئة الجديدة
                products = self.env['product.product'].search(
                    [('categ_id', '=', new_categ_id)], order='id'
                )

                # حدّث default_code لكل المنتجات بالترتيب
                for idx, product in enumerate(products, start=1):
                    product.with_context(skip_product_write=True).write({
                        'default_code': f"{get_category_symbol_sequence}-{str(idx).zfill(5)}"
                    })

        return res


