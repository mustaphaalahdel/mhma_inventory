from odoo import _, models, fields, api
from odoo.exceptions import UserError

class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "mail.thread", "mail.activity.mixin"]

    _order = 'date asc'

    inventory_unit = fields.Char(related='product_id.inventory_unit', store=True)
    standard_pricee = fields.Float(related='product_id.standard_price')
    stock_move_line_cost = fields.Float(
        compute='_compute_stock_move_line_cost', 
        store=True, 
        readonly=False,
        group_operator='avg',
        tracking=True,
    )
    qty_availablee = fields.Float(
        related='product_id.qty_available',
    )
    qty_in_source_location = fields.Float(
        default=0.0, 
        compute='_compute_qty_in_source_location',
    )
    
    @api.depends('product_id', 'product_id.qty_available')
    def _compute_qty_in_source_location(self):
        for record in self:
            quants = 0.0
            if record.location_id.usage == 'internal':
                stock_quants = self.env['stock.quant'].search([
                    ('product_id.id', '=', record.product_id.id),
                    ('location_id.id', 'child_of', record.location_id.id)
                ])
                for stock_quant in stock_quants:
                    quants = quants + stock_quant.quantity
            record.qty_in_source_location = quants
    
    category_id = fields.Many2one(
        string='Category',
        related='product_id.categ_id',
        store=True,
    )
    category_name = fields.Char(related='category_id.name', string='Category Name', store=True,)
    product_ref = fields.Char(related='product_id.default_code', string='Reference', store=True,)
    product_name = fields.Char(related='product_id.name', string='Product Name', store=True,)
    introductory_qty = fields.Float(
        compute='_compute_introductory_qty', 
        store=True, 
        readonly=False,
        group_operator='sum',
        tracking=True,
    )
    virtual_availablee = fields.Float(related='product_id.virtual_available')
    product_dsbrs_type = fields.Selection(related='product_id.product_dsbrs_type')
    # product_dsbrs_type = fields.Float(related='product_id.product_dsbrs_type')
    total_stock_move = fields.Float(
        string='Total Stock Move', 
        compute='_compute_total_stock_move2',
        store=True,
        group_operator='sum'
    )

    # location_usage = fields.Selection(related='location_id.usage')
    # location_dest_usage = fields.Selection(related='location_dest_id.usage')

    introductory_val = fields.Float(compute='_compute_introductory_val', store=True, group_operator='sum')
    incoming_qty = fields.Float(compute='_compute_incoming_qty', store=True, group_operator='sum')
    incoming_val = fields.Float(compute='_compute_incoming_val', store=True, group_operator='sum')
    outgoing_qty = fields.Float(compute='_compute_outgoing_qty', store=True, group_operator='sum')
    outgoing_val = fields.Float(compute='_compute_outgoing_val', store=True, group_operator='sum')
    final_balance = fields.Float(compute='_compute_final_balance', store=True, group_operator='sum')
    final_balance_val = fields.Float(compute='_compute_final_balance_val', store=True, group_operator='sum')
    qty_move = fields.Float(compute='_compute_qty_move', store=True, group_operator='sum', tracking=True)

    partner_move_id = fields.Many2one(
        related='picking_id.partner_id', 
        string='Move Partner',
        readonly=True,
        store=True,
    )

    depart_id = fields.Many2one(
        related='picking_id.depart_id', 
        readonly=True,
        store=True,
    )
    

    @api.depends('quantity', 'introductory_qty', 'stock_move_line_cost', 'line_discount')
    def _compute_introductory_val(self):
        for move in self:
            move.introductory_val = move.introductory_qty * (move.stock_move_line_cost - move.line_discount)

    @api.depends('quantity', 'final_balance', 'stock_move_line_cost', 'line_discount')
    def _compute_final_balance_val(self):
        for move in self:
            move.final_balance_val = move.final_balance * (move.stock_move_line_cost - move.line_discount)

    @api.depends('quantity',)
    def _compute_incoming_qty(self):
        for move in self:
            if(move.location_usage not in ('internal','transit')) and (move.location_dest_usage in ('internal','transit')):
                move.incoming_qty = move.quantity
            elif(move.location_usage in ('supplier')) and (move.location_dest_usage in ('view')):
                move.incoming_qty = move.quantity
            # else:
            #     move.incoming_qty = 0
    @api.depends('quantity', 'stock_move_line_cost', 'line_discount')
    def _compute_incoming_val(self):
        for move in self:
            if(move.location_usage not in ('internal','transit')) and (move.location_dest_usage in ('internal','transit')):
                move.incoming_val = move.quantity * (move.stock_move_line_cost - move.line_discount)
            elif(move.location_usage in ('supplier')) and (move.location_dest_usage in ('view')):
                move.incoming_val = move.quantity * (move.stock_move_line_cost - move.line_discount)
            # else:
            #     move.incoming_val = 0

    @api.depends('quantity',)
    def _compute_outgoing_qty(self):
        for move in self:
            if(move.location_usage in ('internal','transit')) and (move.location_dest_usage not in ('internal','transit')):
                move.outgoing_qty = move.quantity
            elif(move.location_usage in ('view')) and (move.location_dest_usage in ('customer')):
                move.outgoing_qty = move.quantity
            # else:
            #     move.outgoing_qty = 0
    @api.depends('quantity', 'stock_move_line_cost', 'line_discount')
    def _compute_outgoing_val(self):
        for move in self:
            if(move.location_usage in ('internal','transit')) and (move.location_dest_usage not in ('internal','transit')):
                move.outgoing_val = move.quantity * (move.stock_move_line_cost - move.line_discount)
            elif(move.location_usage in ('view')) and (move.location_dest_usage in ('customer')):
                move.outgoing_val = move.quantity * (move.stock_move_line_cost - move.line_discount)
            # else:
            #     move.outgoing_val = 0

    @api.depends('quantity')
    def _compute_qty_move(self):
        for move in self:
            # try: 
                if(move.location_usage not in ('internal','transit')) and (move.location_dest_usage in ('internal','transit')):
                    move.qty_move = move.quantity
                elif(move.location_usage in ('supplier')) and (move.location_dest_usage in ('view')):
                    move.qty_move = move.quantity
                elif(move.location_usage in ('internal','transit')) and (move.location_dest_usage not in ('internal','transit')):
                    move.qty_move = move.quantity * -1
                elif(move.location_usage in ('view')) and (move.location_dest_usage in ('customer')):
                    move.qty_move = move.quantity * -1
                else:
                    print(f"prodect default code: {move.product_id.default_code}, product: {move.product_id.name}, location_usage: {move.location_usage}, location_dest_usage: {move.location_dest_usage}")
                    move.qty_move = move.quantity
            # except Exception as e:
            #     move.qty_move = 0


    @api.depends('introductory_qty', 'incoming_qty', 'outgoing_qty')
    def _compute_final_balance(self):
        for move in self:
            move.final_balance = move.introductory_qty + move.incoming_qty - move.outgoing_qty

    @api.depends('product_id.qty_available', 'product_uom_qty', 'quantity', 'state')
    def _compute_introductory_qty(self):
        for move in self:      
            if(move.state == 'draft' or move.state == 'assigned'):
                move.introductory_qty = move.product_id.qty_available


    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            product_id = vals.get('product_id')
            if product_id:
                product = self.env['product.product'].browse(product_id)
                vals['introductory_qty'] = product.qty_available
                vals['stock_move_line_cost'] = product.standard_price
                if product.detailed_type == 'consu' and vals['state'] in ('assigned', 'done', 'partially_available'):
                    if (product.qty_from_valuation + vals['qty_move']) < 0:
                        raise UserError(_(f"Error create: The Product {product.display_name} is consumable will be quantity {product.qty_from_valuation + vals['qty_move']}. Quantity {vals['quantity']} must be less than or equal to the quantity from Valuation {product.qty_from_valuation}."))
        records = super().create(vals_list)

        # seq stock move
        if not self.env.context.get("keep_line_sequence", False):
            records.picking_id._reset_sequence()


        return records
    
    # def write(self, vals):
    #     records = super().write(vals)
    #     for record in self:
    #         stock_valuations = self.env['stock.valuation.layer'].search([
    #             ('stock_move_id', '=', record.id),
    #             ('reference', '=', record.reference)
    #         ])
    #         for stock_valuation in stock_valuations:
    #             stock_valuation.write({
    #                 # 'cost': vals.get('stock_move_line_cost')
    #                 'unit_cost': record.actual_cost,
    #                 'value': record.actual_cost * stock_valuation.quantity
    #             })
    #     return records
    
    def write(self, vals_list):            
        records = super().write(vals_list)
        for record in self:
            if record.product_id.detailed_type == 'consu':
                print(f"record.product_id.qty_from_valuation: {record.product_id.qty_from_valuation}")
                print(f"record.quantity: {record.qty_move}")
                print(f"resultt: {record.product_id.qty_from_valuation + record.qty_move}, {record.state}")
                if record.state in ('done', 'assigned', 'partially_available'):
                    print(f"resultt22: {record.product_id.qty_from_valuation + record.qty_move}")
                    if (record.product_id.qty_from_valuation + record.qty_move) < 0:
                        raise UserError(_(f"Error update: The product {record.product_id.display_name} is consumable will be quantity {record.product_id.qty_from_valuation + record.qty_move}. Quantity {record.quantity} must be less than or equal to the quantity from Valuation {record.product_id.qty_from_valuation}."))
        return records

    line_discount = fields.Float(
        compute='_compute_stock_move_line_cost',
        store=True,
        readonly=False,
        default=0,
        tracking=True,
    )

    actual_cost = fields.Float(
        compute='_compute_actual_cost',
        store=True,
        readonly=True,
        default=0,
        group_operator='avg'
    )

    @api.depends('product_id.standard_price', 'product_uom_qty', 'quantity', 'state', 'price_unit')
    def _compute_stock_move_line_cost(self):
        for move in self:
            if(move.state != 'done' and move.state != 'cancel'):
                print(f"move.price_unit: {move.price_unit}")
                if(len(move.group_id.stock_move_ids) == 0):
                    move.stock_move_line_cost = move.product_id.standard_price
                elif(len(move.group_id.stock_move_ids) > 0):
                    if("P" in move.group_id.name and move.picking_type_id.code == "incoming"):
                        move.stock_move_line_cost = move.price_unit
                        purchase_id = self.env["purchase.order"].search([("name", "=", move.group_id.name)])
                        for line in purchase_id.order_line:
                            if(move.product_id == line.product_id):
                                move.line_discount = (move.price_unit * (line.discount / 100))
                        
                        # for line in move.group_id.stock_move_ids:
                        #     if(move.product_id == line.product_id):
                        #         move.stock_move_line_cost = line.price_unit * (line.price / 100)
                        
                    else:
                        move.stock_move_line_cost = move.product_id.standard_price

    @api.depends('stock_move_line_cost', 'line_discount')
    def _compute_actual_cost(self):
        for move in self:
            move.actual_cost = move.stock_move_line_cost - move.line_discount
            
    qty_stock_move = fields.Float(
        compute='_compute_qty_stock_move',
    )
    
    @api.depends('product_id.qty_available')
    def _compute_qty_stock_move(self):
        for move in self:
            # factor_inv = move.product_uom.factor_inv
            if move.product_id.uom_id.ratio:
                factor_inv = move.product_uom.ratio / move.product_id.uom_id.ratio
            else:
                factor_inv = 1
            if(move.quantity == 0.0):
                move.qty_stock_move = move.product_uom_qty * factor_inv
            else:
                move.qty_stock_move = move.quantity * factor_inv

    @api.depends('stock_move_line_cost', 'line_discount', 'product_uom_qty', 'quantity')
    def _compute_total_stock_move2(self):
        for move in self:
            
            if move.product_id.uom_id.ratio:    
                factor_inv = move.product_uom.ratio / move.product_id.uom_id.ratio
            else:
                factor_inv = 1

            if(move.quantity == 0.0):
                move.total_stock_move = (move.stock_move_line_cost - move.line_discount) * (move.product_uom_qty * factor_inv)
            else:
                move.total_stock_move = (move.stock_move_line_cost - move.line_discount) * (move.quantity * factor_inv)
            if(move.location_usage in ('internal','transit')) and (move.location_dest_usage not in ('internal','transit')):
                move.total_stock_move = move.total_stock_move * -1
            elif (move.location_id.usage in ('view',)) and (move.location_dest_id.usage in ('customer',)):
                move.total_stock_move = move.total_stock_move * -1



    # show sum column to field store = false
    @api.model 
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(StockMove, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        
        # if all(x in fields for x in [
        #     'introductory_val', 
        #     'incoming_val', 
        #     'outgoing_val', 
        #     'final_balance_val', 
        #     'total_stock_move',

        #     'introductory_qty',
        #     'qty_move',
        #     'incoming_qty',
        #     'outgoing_qty',
        #     'final_balance',
        # ]):
        #     for line in res:
        #         if '__domain' in line:
        #             lines = self.search(line['__domain'])
        #             a = 0.0
        #             b = 0.0
        #             c = 0.0
        #             d = 0.0
        #             e = 0.0

        #             f = 0.0
        #             g = 0.0
        #             h = 0.0
        #             i = 0.0
        #             j = 0.0
        #             for record in lines:
        #                 a += record.introductory_val
        #                 b += record.incoming_val
        #                 c += record.outgoing_val
        #                 d += record.final_balance_val
        #                 e += record.total_stock_move

        #                 f += record.introductory_qty
        #                 g += record.qty_move
        #                 h += record.incoming_qty
        #                 i += record.outgoing_qty
        #                 j += record.final_balance
        #             line['introductory_val'] = a
        #             line['incoming_val'] = b
        #             line['outgoing_val'] = c
        #             line['final_balance_val'] = d
        #             line['total_stock_move'] = e

        #             line['introductory_qty'] = f
        #             line['qty_move'] = g
        #             line['incoming_qty'] = h
        #             line['outgoing_qty'] = i
        #             line['final_balance'] = j
        
        return res
    
    qty_balances_computed = fields.Boolean(
        string='Balances Computed',
        default=False,
        store=True
    )

    def action_set_qty_balances_computed_false(self):
        query = """
            UPDATE stock_move
            SET qty_balances_computed = FALSE
        """
        self.env.cr.execute(query)
        self.env.invalidate_all()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Balances computed flag has been reset for all records. Please refresh the page.',
                'type': 'success',
                'sticky': False,
            }
        }
        
    def action_compute_qty_balances(self):
        query = """
            WITH products_to_update AS (
                SELECT DISTINCT product_id
                FROM stock_move
                WHERE qty_balances_computed IS NOT TRUE
            ),
            computed_balances AS (
                SELECT
                    id,
                    quantity,
                    actual_cost,
                    SUM(quantity) OVER (
                        PARTITION BY product_id
                        ORDER BY date, id
                    ) AS running_total
                FROM
                    stock_move
                WHERE
                    product_id IN (SELECT product_id FROM products_to_update)
            )
            UPDATE
                stock_move sm
            SET
                final_balance = cb.running_total,
                introductory_qty = cb.running_total - sm.quantity,
                final_balance_val = cb.running_total * cb.actual_cost,
                introductory_val = (cb.running_total - sm.quantity) * cb.actual_cost,
                qty_balances_computed = TRUE
            FROM
                computed_balances cb
            WHERE
                sm.id = cb.id;
        """
        self.env.cr.execute(query)
        self.env.invalidate_all()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Balances have been recomputed successfully. Please refresh the page.',
                'type': 'success',
                'sticky': False,
            }
        }

    # seq stock move
    # re-defines the field to change the default
    sequence = fields.Integer("HiddenSequence", default=9999)

    # displays sequence on the stock moves
    sequence2 = fields.Integer(
        "Sequence",
        help="Shows the sequence in the Stock Move.",
        related="sequence",
        readonly=True,
        store=True,
    )


