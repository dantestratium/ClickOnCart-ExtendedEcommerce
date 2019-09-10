from odoo import fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    is_delivery_partner = fields.Boolean('Is a Delivery Partner', default=False)
    delivery_count = fields.Integer(string='Delivery Count')
