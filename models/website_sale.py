import random

from odoo import api, fields, models


class ProductPublicCategory(models.Model):
    _inherit = "product.public.category"

    icon = fields.Binary(attachment=True, string="Icon", help="This field holds the image used as icon for the category, limited to 24x24.")
    product_ids = fields.Many2many('product.template', string='Products')

    @api.multi
    def _randomize(self, count=0):
        length = len(self)

        if count > 0:
            length = count

        return random.sample(self, length)

    @api.multi
    def _get_random_index(self):
        return random.randint(0, (len(self.child_id) - 1))

    @api.multi
    def _get_random_product(self):
        if len(self.product_ids) < 4:
            return self.product_ids

        return random.sample(self.product_ids, 1)

    @api.multi
    def _get_brands(self):
        brands = []

        for product in self.product_ids:
            if product.brand_id not in brands:
                brands.append(product.brand_id)

        return brands
