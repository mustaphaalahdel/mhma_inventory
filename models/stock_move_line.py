from odoo import models, fields, api
from datetime import datetime


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    inventory_unit = fields.Char(related='product_id.inventory_unit', readonly=True, store=True)
    depart_id = fields.Many2one(related='picking_id.depart_id', readonly=True, store=True)
    
    schedule_date_to_picking = fields.Datetime(
        related='picking_id.scheduled_date', 
        readonly=True, 
        store=True,
    )
    date_done_to_picking = fields.Datetime(
        related='picking_id.date_done', 
        readonly=True, 
        store=True,
    )

    @api.onchange('expiration_date')
    def set_val_to_lot_name(self):
        if 'expiration_date' in self._fields and self.expiration_date:
            exp_date = self.expiration_date
            if isinstance(exp_date, str):
                exp_date = fields.Datetime.from_string(exp_date)
            if not self.lot_name:
                self.lot_name = exp_date.strftime("%d%m%y")
                
    @api.model
    def create(self, vals):
        records = super().create(vals)
        # تأكد أن records ممكن يكون سجل واحد أو مجموعة
        for record in records:
            if 'expiration_date' in record._fields and record.expiration_date:
                exp_date = record.expiration_date
                if isinstance(exp_date, str):
                    exp_date = fields.Datetime.from_string(exp_date)
                if not record.lot_name:
                    record.lot_name = exp_date.strftime("%d%m%y")
        return records


    # # seq line
    # def _get_aggregated_product_quantities(self, **kwargs):
    #     aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
    #     for move_line in self:
    #         line_key = self._get_aggregated_properties(move_line=move_line)["line_key"]
    #         sequence2 = move_line.move_id.sequence2
    #         if line_key in aggregated_move_lines:
    #             aggregated_move_lines[line_key]["sequence2"] = sequence2

    #     return aggregated_move_lines


    # seq line
    def _get_aggregated_product_quantities(self, **kwargs):
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        for move_line in self:
            move = move_line.move_id
            product = move.product_id
            uom = move.product_uom or move_line.product_uom_id
            description = move.description_picking
            name = product.display_name
            if description in (name, product.name):
                description = False
            # 🔑 هذا هو نفس line_key المستخدم في Odoo 17
            line_key = (
                f"{product.id}_"
                f"{product.display_name}_"
                f"{description or ''}_"
                f"{uom.id}_"
                f"{move.product_packaging_id or ''}"
            )
            if line_key in aggregated_move_lines:
                aggregated_move_lines[line_key]["sequence2"] = move.sequence
        return aggregated_move_lines

