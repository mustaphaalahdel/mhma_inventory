from odoo import models, fields, api
from collections import defaultdict
from datetime import datetime


class StockPickingSeq(models.Model):
    _inherit = 'stock.picking'

    order_number = fields.Integer(
        string='Order Number',
        index=True,
        copy=False
    )

    def _resequence_yearly_operations(self):
        groups = defaultdict(lambda: self.env['stock.picking'])

        for record in self.filtered(lambda r: r.scheduled_date and r.picking_type_id):
            scheduled_dt = fields.Datetime.context_timestamp(self, record.scheduled_date)
            if not scheduled_dt:
                continue

            year = scheduled_dt.year
            groups[(record.picking_type_id.id, year)] |= record

        for (picking_type_id, year), records in groups.items():
            date_from = datetime(year, 1, 1)
            date_to = datetime(year, 12, 31, 23, 59, 59)

            domain = [
                ('picking_type_id', '=', picking_type_id),
                ('scheduled_date', '>=', date_from),
                ('scheduled_date', '<=', date_to),
                ('state', '!=', 'cancel'),
            ]

            pickings = self.search(domain, order='scheduled_date asc, id asc')

            updates = []
            number = 1
            for picking in pickings:
                if picking.order_number != number:
                    updates.append((picking.id, number))
                number += 1

            for picking_id, number in updates:
                self.env['stock.picking'].browse(picking_id).write({
                    'order_number': number
                })

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._resequence_yearly_operations()
        return records

    def write(self, vals):
        affected = self
        res = super().write(vals)

        if {'scheduled_date', 'picking_type_id'} & vals.keys():
            affected._resequence_yearly_operations()

        return res
