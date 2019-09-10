import math
import random

from itertools import chain

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one('product.brand', string="Product Brand")
    description_ecommerce = fields.Text(string="eCommerce Description")

    @api.multi
    def _ratings_val_integer(self):
        return math.floor(self.rating_get_stats([('website_published', '=', True)])['avg'])

    @api.multi
    def _ratings_val_decimal(self):
        return self.rating_get_stats([('website_published', '=', True)])['avg'] - self._ratings_val_integer()

    @api.multi
    def _ratings_empty_star(self):
        return 5 - (self._ratings_val_integer() + math.ceil(self._ratings_val_decimal()))

    @api.multi
    def _ratings_val_integer_range(self):
        return range(0, self._ratings_val_integer())

    @api.multi
    def _ratings_empty_star_range(self):
        return range(0, self._ratings_empty_star())

    @api.multi
    def _randomize(self, count=0):
        length = len(self)

        if count > 0:
            length = count

        return random.sample(self, length)

    @api.multi
    def _random_products(self, brand_ids=False):
        results = []
        query = """SELECT id
                        FROM product_template
                        WHERE active = %(active)s"""

        if brand_ids:
            query += "AND brand_id = ANY(%(brands)s)"

        query += " ORDER BY random() LIMIT 20"
        query_args = {'active': '1', 'brands': brand_ids}

        self._cr.execute(query, query_args)

        item_ids = [x[0] for x in self._cr.fetchall()]

        prods = self.env['product.template'].sudo().browse(item_ids)

        for prod in prods:
            if prod.website_published:
                results.append(prod)

        return results


class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brands'
    _order = 'sequence'

    sequence = fields.Integer(help="Gives the sequence order when displaying "
                                   "a list of rules.")
    name = fields.Char(string='Name', required=True, translate=True)
    brand_image = fields.Binary(string='Brand Image')
    product_ids = fields.One2many('product.template', 'brand_id')

    _sql_constraints = [('name_uniq', 'unique (name)',
                         'Brand name already exists !')]

    @api.multi
    def generate(self, count=6):
        brands = self.search([], limit=12)

        return random.sample(brands.filtered(lambda x: len(x.product_ids) > 5), count)


class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    categ_id = fields.Many2one(
        'product.public.category', 'eCommerce Category', ondelete='cascade',
        help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise.")
    brand_id = fields.Many2one(
        'product.brand', 'Product Brand', ondelete='cascade')
    sale_event_id = fields.Many2one(
        'website.sale.event', 'Sale Event', ondelete='cascade')
    applied_on = fields.Selection([
        ('5_sale_event', 'Sale Event'),
        ('4_product_brand', 'Product Brand'),
        ('3_global', 'Global'),
        ('2_product_category', ' Product Category'),
        ('1_product', 'Product'),
        ('0_product_variant', 'Product Variant')], "Apply On",
        default='3_global', required=True,
        help='Pricelist Item applicable on selected option')

    @api.one
    @api.depends('sale_event_id', 'brand_id', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price',
                 'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):
        res = super(PricelistItem, self)._get_pricelist_item_name_price()
        if self.brand_id:
            self.name = _("Brand: %s") % (self.brand_id.name)

        if self.sale_event_id:
            self.name = _("Event: %s") % (self.sale_event_id.name)

        return res

class Pricelist(models.Model):
    _inherit = 'product.pricelist'

    @api.multi
    def _compute_price_rule(self, products_qty_partner, date=False, uom_id=False):
        """ Low-level method - Mono pricelist, multi products
        Returns: dict{product_id: (price, suitable_rule) for the given pricelist}

        If date in context: Date of the pricelist (%Y-%m-%d)

            :param products_qty_partner: list of typles products, quantity, partner
            :param datetime date: validity date
            :param ID uom_id: intermediate unit of measure
        """

        self.ensure_one()
        if not date:
            date = self._context.get('date') or fields.Date.context_today(self)
        if not uom_id and self._context.get('uom'):
            uom_id = self._context['uom']
        if uom_id:
            # rebrowse with uom if given
            products = [item[0].with_context(uom=uom_id) for item in products_qty_partner]
            products_qty_partner = [(products[index], data_struct[1], data_struct[2]) for index, data_struct in
                                    enumerate(products_qty_partner)]
        else:
            products = [item[0] for item in products_qty_partner]

        if not products:
            return {}

        categ_ids = {}
        brand_ids = {}
        for p in products:
            brand_ids[p.brand_id.id] = True
            categ = p.public_categ_ids
            for c in categ:
                categ_ids[c.id] = True
        categ_ids = list(categ_ids)
        brand_ids = list(brand_ids)

        is_product_template = products[0]._name == "product.template"
        if is_product_template:
            prod_tmpl_ids = [tmpl.id for tmpl in products]
            # all variants of all products
            prod_ids = [p.id for p in
                        list(chain.from_iterable([t.product_variant_ids for t in products]))]
        else:
            prod_ids = [product.id for product in products]
            prod_tmpl_ids = [product.product_tmpl_id.id for product in products]

        # Load all rules
        self._cr.execute(
            'SELECT item.id '
            'FROM product_pricelist_item AS item '
            'LEFT JOIN product_public_category AS categ '
            'ON item.categ_id = categ.id '
            'WHERE (item.product_tmpl_id IS NULL OR item.product_tmpl_id = any(%s))'
            'AND (item.product_id IS NULL OR item.product_id = any(%s))'
            'AND (item.categ_id IS NULL OR item.categ_id = any(%s)) '
            'AND (item.brand_id IS NULL OR item.brand_id = any(%s)) '
            'AND (item.pricelist_id = %s) '
            'AND (item.date_start IS NULL OR item.date_start<=%s) '
            'AND (item.date_end IS NULL OR item.date_end>=%s)'
            'ORDER BY item.applied_on, item.min_quantity desc, categ.name desc, item.id desc',
            (prod_tmpl_ids, prod_ids, categ_ids, brand_ids, self.id, date, date))
        # NOTE: if you change `order by` on that query, make sure it matches
        # _order from model to avoid inconstencies and undeterministic issues.

        item_ids = [x[0] for x in self._cr.fetchall()]
        items = self.env['product.pricelist.item'].browse(item_ids)
        results = {}
        for product, qty, partner in products_qty_partner:
            results[product.id] = 0.0
            suitable_rule = False

            # Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
            # An intermediary unit price may be computed according to a different UoM, in
            # which case the price_uom_id contains that UoM.
            # The final price will be converted to match `qty_uom_id`.
            qty_uom_id = self._context.get('uom') or product.uom_id.id
            price_uom_id = product.uom_id.id
            qty_in_product_uom = qty
            if qty_uom_id != product.uom_id.id:
                try:
                    qty_in_product_uom = self.env['uom.uom'].browse([self._context['uom']])._compute_quantity(qty,
                                                                                                              product.uom_id)
                except UserError:
                    # Ignored - incompatible UoM in context, use default product UoM
                    pass

            # if Public user try to access standard price from website sale, need to call price_compute.
            # TDE SURPRISE: product can actually be a template
            price = product.price_compute('list_price')[product.id]

            price_uom = self.env['uom.uom'].browse([qty_uom_id])
            for rule in items:
                if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
                    continue
                if is_product_template:
                    if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and not (
                            product.product_variant_count == 1 and product.product_variant_id.id == rule.product_id.id):
                        # product rule acceptable on template if has only one variant
                        continue
                else:
                    if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and product.id != rule.product_id.id:
                        continue

                if rule.categ_id:
                    cat = product.public_categ_ids
                    cat_flag = False
                    for c in cat:
                        if c.id == rule.categ_id.id:
                            cat_flag = True

                    if not cat_flag:
                        continue

                if rule.brand_id and rule.brand_id.id != product.brand_id.id:
                    continue

                if rule.sale_event_id:
                    sale_prod = rule.sale_event_id.product_ids
                    sale_prod_flag = False
                    for s in sale_prod:
                        if s.id == product.product_tmpl_id.id:
                            sale_prod_flag = True

                    if not sale_prod_flag:
                        continue

                if rule.base == 'pricelist' and rule.base_pricelist_id:
                    price_tmp = rule.base_pricelist_id._compute_price_rule([(product, qty, partner)])[product.id][
                        0]  # TDE: 0 = price, 1 = rule
                    price = rule.base_pricelist_id.currency_id._convert(price_tmp, self.currency_id,
                                                                        self.env.user.company_id, date, round=False)
                else:
                    # if base option is public price take sale price else cost price of product
                    # price_compute returns the price in the context UoM, i.e. qty_uom_id
                    price = product.price_compute(rule.base)[product.id]

                convert_to_price_uom = (lambda price: product.uom_id._compute_price(price, price_uom))

                if price is not False:
                    if rule.compute_price == 'fixed':
                        price = convert_to_price_uom(rule.fixed_price)
                    elif rule.compute_price == 'percentage':
                        price = (price - (price * (rule.percent_price / 100))) or 0.0
                    else:
                        # complete formula
                        price_limit = price
                        price = (price - (price * (rule.price_discount / 100))) or 0.0
                        if rule.price_round:
                            price = tools.float_round(price, precision_rounding=rule.price_round)

                        if rule.price_surcharge:
                            price_surcharge = convert_to_price_uom(rule.price_surcharge)
                            price += price_surcharge

                        if rule.price_min_margin:
                            price_min_margin = convert_to_price_uom(rule.price_min_margin)
                            price = max(price, price_limit + price_min_margin)

                        if rule.price_max_margin:
                            price_max_margin = convert_to_price_uom(rule.price_max_margin)
                            price = min(price, price_limit + price_max_margin)
                    suitable_rule = rule
                break
            # Final price conversion into pricelist currency
            if suitable_rule and suitable_rule.compute_price != 'fixed' and suitable_rule.base != 'pricelist':
                if suitable_rule.base == 'standard_price':
                    cur = product.cost_currency_id
                else:
                    cur = product.currency_id
                price = cur._convert(price, self.currency_id, self.env.user.company_id, date, round=False)

            results[product.id] = (price, suitable_rule and suitable_rule.id or False)

        return results
