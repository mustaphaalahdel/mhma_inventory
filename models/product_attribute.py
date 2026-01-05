from odoo import fields, models


class ProductAttribute(models.Model):
    _inherit = "product.attribute"


class ProductTemplateAttributeLine(models.Model):
    _inherit = "product.template.attribute.line"

    sequence = fields.Integer(help="Determine the display order", index=True)


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    def _get_combination_name(self):
        """Gets the combination name of all the attributes.
        If active, it will display the name or short name before its value.
        The order of the attributes is defined by the user"""
        display_ptav_list = []
        for ptav in sorted(self, key=lambda seq: seq.attribute_line_id.sequence):
            display_ptav_list.append(ptav.name)
        return ", ".join(display_ptav_list)
