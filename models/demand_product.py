from odoo import _, models, fields, api

class DemandProduct(models.Model):
    _name = 'mhma.demand.product'
    _description = 'Demand Product'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    active = fields.Boolean(default=True)

    name = fields.Char(required=True, tracking=True)
    keywords = fields.Char()
    image = fields.Binary()
    categ_id = fields.Many2one(
        required=True,
        comodel_name='product.category', 
        string='Product Category',
        default=lambda self: self.env.ref('product.product_category_all'),
    )
    uom_id = fields.Many2one(
        required=True,
        comodel_name='uom.uom', 
        string='Unit of Measure',
        default=lambda self: self.env.ref('uom.product_uom_unit'),
    )
    estimated_cost = fields.Float()
    desc = fields.Text(string='Description')
    type = fields.Selection(
        string="Product Disbursement Type",
        selection=[
            ("1", "Commodity product"),
            ("2", "Fixed Asset"),
            ("3", "Service"),
        ],
    )
    detail = fields.Html(string='Detail')
    
    access_group_ids = fields.Many2many(
        comodel_name='res.groups', 
        relation='mhma_demand_product_access_group_rel',
        column1='demand_product_id',
        column2='group_id',
        string="Access Groups",
        # default=lambda self:self.env[ 'res.groups' ].search([('id', '=', '1')]).ids
    )
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('keywords', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()
    

