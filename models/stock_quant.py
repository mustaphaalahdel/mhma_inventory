# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def action_clear_ghost_reserved(self):
        # Selected records
        quants = self
        if not quants:
            quants = self.env["stock.quant"].browse(self.env.context.get("active_ids", []))

        if not quants:
            raise UserError(_("Please select records first."))

        # Only records that have reserved quantity
        quants = quants.filtered(lambda q: q.reserved_quantity and q.reserved_quantity > 0)
        if not quants:
            raise UserError(_("The selected records do not have any reserved quantity."))

        MoveLine = self.env["stock.move.line"]

        # Choose the correct quantity field on stock.move.line (depends on version/database)
        if "product_uom_qty" in MoveLine._fields:
            qty_field = "product_uom_qty"
        elif "quantity" in MoveLine._fields:
            qty_field = "quantity"
        else:
            raise UserError(_("Could not find a quantity field on stock.move.line (product_uom_qty or quantity)."))

        conflicts = []
        to_clear = self.env["stock.quant"]

        for q in quants:
            # Your condition: if there is a Move Line in assigned (or partially_available) state, do not clear
            domain = [
                ("product_id", "=", q.product_id.id),
                ("location_id", "=", q.location_id.id),
                (qty_field, ">", 0),
                ("move_id.state", "in", ("assigned", "partially_available")),
            ]
            if q.company_id:
                domain.append(("company_id", "=", q.company_id.id))

            ml = MoveLine.search(domain, limit=1)
            if ml:
                ref = ml.picking_id.name or ml.move_id.reference or ml.move_id.name or "-"
                conflicts.append(
                    f"- Product: {q.product_id.display_name} | Location: {q.location_id.complete_name} | Document: {ref}"
                )
            else:
                # No actual move lines => ghost reservation
                to_clear |= q

        if conflicts:
            raise UserError(
                _("Cannot clear the reservation because there are actual reservations (assigned/partially available) on some selected records:\n\n%s")
                % "\n".join(conflicts)
            )

        to_clear.write({"reserved_quantity": 0.0})
        return {"type": "ir.actions.client", "tag": "reload"}
