from odoo import models, fields, api

class ProductCategory(models.Model):
    _inherit = 'product.category'

    symbol = fields.Char(default='0')
    
    product_variant_ids = fields.One2many(
        'product.product', 
        'categ_id', 
        string="Products",
    )
    
    product_variant_count = fields.Integer(
        compute='_compute_product_variant_count',
        string="Product Variant Count",
        store=True,
    )
    
    @api.depends('product_variant_ids')
    def _compute_product_variant_count(self):
        for category in self:
            category.product_variant_count = len(category.product_variant_ids)
    

