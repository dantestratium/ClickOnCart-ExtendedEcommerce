import random
import json

from odoo.http import request
from odoo import fields, http, _
from datetime import datetime, time
from werkzeug.exceptions import NotFound
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.backend import WebsiteSaleBackend
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.http_routing.models.ir_http import slug
from operator import itemgetter
from odoo.exceptions import UserError

PPG = 20  # Products Per Page
PPR = 4   # Products Per Row


class ExtendWebsiteSaleBackend(WebsiteSaleBackend):

    @http.route()
    def fetch_dashboard_data(self, website_id, date_from, date_to):
        Website = request.env['website']
        current_website = website_id and Website.browse(website_id) or Website.get_current_website()

        results = super(ExtendWebsiteSaleBackend, self).fetch_dashboard_data(website_id, date_from, date_to)

        date_date_from = fields.Date.from_string(date_from)
        date_date_to = fields.Date.from_string(date_to)
        date_diff_days = (date_date_to - date_date_from).days
        datetime_from = datetime.combine(date_date_from, time.min)
        datetime_to = datetime.combine(date_date_to, time.max)

        sale_order_domain = [
            ('website_id', '=', current_website.id),
            ('team_id', 'in', request.env['crm.team'].search([('team_type', '=', 'website')]).ids),
            ('date_order', '>=', fields.Datetime.to_string(datetime_from)),
            ('date_order', '<=', fields.Datetime.to_string(datetime_to))]

        report_price_lines = request.env['sale.report'].read_group(
            domain=[
                ('website_id', '=', current_website.id),
                ('team_id.team_type', '=', 'website'),
                ('state', 'in', ['sale', 'done']),
                ('date', '>=', date_from),
                ('date', '<=', date_to)],
            fields=['team_id', 'price_subtotal'],
            groupby=['team_id'],
        )

        results['dashboards']['sales']['summary'].update(
            order_to_invoice_count=request.env['sale.order'].search_count(sale_order_domain + [
                ('state', 'in', ['sale']),
                ('order_line', '!=', False),
                ('partner_id', '!=', request.env.ref('base.public_partner').id),
                ('status_desc', '=', 'delivery'),
                ('invoice_status', '=', 'to invoice'),
            ]),
            order_carts_abandoned_count=request.env['sale.order'].search_count(sale_order_domain + [
                ('is_abandoned_cart', '=', True),
                ('cart_recovery_email_sent', '=', False)
            ]),
            payment_to_capture_count=request.env['sale.order'].search_count([
                ('state', 'in', ['sale', 'done']),
                ('status_desc', 'in', ['received', 'delivered']),
                ('partner_id', '!=', request.env.ref('base.public_partner').id),
            ]),
            total_sold=sum(price_line['price_subtotal'] for price_line in report_price_lines)
        )

        return results


class ExtendWebsiteSale(WebsiteSale):

    def _get_search_domain(self, search, category, attrib_values, brand_values):
        domain = request.website.sale_product_domain()
        if search:
            for srch in search.split(" "):
                domain += [
                    '|', '|', '|', '|', ('name', 'ilike', srch), ('description', 'ilike', srch),
                    ('description_sale', 'ilike', srch), ('product_variant_ids.default_code', 'ilike', srch),
                    ('brand_id.name', 'ilike', srch)]

        if category:
            domain += [('public_categ_ids', 'child_of', int(category))]

        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domain += [('attribute_line_ids.value_ids', 'in', ids)]
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domain += [('attribute_line_ids.value_ids', 'in', ids)]

        if brand_values:
            domain += [('brand_id', 'in', brand_values)]

        return domain

    @http.route()
    def shop(self, page=0, category=None, search='', ppg=False, **post):
        add_qty = int(post.get('add_qty', 1))
        prod_brands = []

        if category:
            category = request.env['product.public.category'].search([('id', '=', int(category))], limit=1)
            if not category or not category.can_access_from_current_website():
                raise NotFound()

            for product in category.product_ids:
                if product.brand_id and product.brand_id not in prod_brands:
                    prod_brands.append(product.brand_id)
        else:
            prod_brands = request.env['product.brand'].search([])

        if ppg:
            try:
                ppg = int(ppg)
            except ValueError:
                ppg = PPG
            post["ppg"] = ppg
        else:
            ppg = PPG

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values}
        attrib_set = {v[1] for v in attrib_values}

        brand_list = request.httprequest.args.getlist('brands')
        brand_values = [list(map(str, v.split("-"))) for v in brand_list if v]
        brand_set = set([int(v[1]) for v in brand_values])

        domain = self._get_search_domain(search, category, attrib_values, list(brand_set))

        keep = QueryURL('/shop', category=category and int(category), search=search, attrib=attrib_list,
                        order=post.get('order'))

        pricelist_context, pricelist = self._get_pricelist_context()

        request.context = dict(request.context, pricelist=pricelist.id, partner=request.env.user.partner_id)

        url = "/shop"
        if search:
            post["search"] = search
        if attrib_list:
            post['attrib'] = attrib_list

        Product = request.env['product.template'].sudo().with_context(bin_size=True)

        Category = request.env['product.public.category']
        search_categories = False
        search_product = Product.search(domain)
        categs = Category.search([('parent_id', '=', False)] + request.website.website_domain())

        parent_category_ids = []
        if category:
            url = "/shop/category/%s" % slug(category)
            parent_category_ids = [category.id]
            current_category = category
            while current_category.parent_id:
                parent_category_ids.append(current_category.parent_id.id)
                current_category = current_category.parent_id

        product_count = len(search_product)

        pager = request.website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        products = Product.search(domain, limit=ppg, offset=pager['offset'], order=self._get_search_order(post))

        if search and product_count:
            prod_brands = []
            for product in products:
                if product.brand_id and product.brand_id not in prod_brands:
                    prod_brands.append(product.brand_id)

            if request.session.get('search_keywords_brands'):
                if products[0].brand_id.id not in request.session['search_keywords_brands']:
                    request.session['search_keywords_brands'].append(products[0].brand_id.id)
            else:
                request.session['search_keywords_brands'] = [products[0].brand_id.id]

        ProductAttribute = request.env['product.attribute']

        if products:
            attributes = ProductAttribute.search([('attribute_line_ids.value_ids', '!=', False),
                                                  ('attribute_line_ids.product_tmpl_id', 'in', search_product.ids)])
        else:
            attributes = ProductAttribute.browse(attributes_ids)

        compute_currency = self._get_compute_currency(pricelist, products[:1])

        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'add_qty': add_qty,
            'products': products,
            'search_count': product_count,  # common for all searchbox
            'bins': TableCompute().process(products, ppg),
            'rows': PPR,
            'categories': categs,
            'attributes': attributes,
            'compute_currency': compute_currency,
            'keep': keep,
            'parent_category_ids': parent_category_ids,
            'search_categories_ids': [],
            'brands': prod_brands,
            'brand_values': brand_values,
            'brand_set': brand_set,
            'brand_by': post.get('brands'),
            'order_by': post.get('order')
        }
        if category:
            values['main_object'] = category
        return request.render("website_sale.products", values)

    @http.route()
    def product(self, product, category='', search='', **kwargs):
        more_categ_array = []
        public_categs = sorted(product.public_categ_ids, key=itemgetter('id'), reverse=True)

        for categ in public_categs:
            result = request.env['product.template'].search([('id', '!=', product.id), ('public_categ_ids', 'child_of', categ.id)])
            count = len(result)

            if count > 10:
                count = 10

            more_categ_array.append({
                'info': categ,
                'products': random.sample(result, count)
            })

        sup = super(ExtendWebsiteSale, self).product(product, category='', search='', **kwargs)
        sup.qcontext['more_from_category'] = more_categ_array

        if request.session.get('search_keywords_brands'):
            if product.brand_id.id not in request.session['search_keywords_brands']:
                request.session['search_keywords_brands'].append(product.brand_id.id)
        else:
            request.session['search_keywords_brands'] = [product.brand_id.id]

        return sup

    @http.route()
    def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, display=True):
        order = request.website.sale_get_order(force_create=1)
        if order.state != 'draft':
            request.website.sale_reset()
            return {}

        value = order._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty)

        if not order.cart_quantity:
            request.website.sale_reset()
            return value

        order = request.website.sale_get_order()

        value['subtotal'] = 0
        for line in order.order_line:
            if line.id == line_id:
                value['subtotal'] = line.price_subtotal

        value['cart_quantity'] = order.cart_quantity
        value['total'] = order.amount_total
        from_currency = order.company_id.currency_id
        to_currency = order.pricelist_id.currency_id

        value['sidecart'] = request.env['ir.ui.view'].render_template("extended_ecommerce.side_cart", {
            'website_sale_order': order,
            'compute_currency': lambda price: from_currency._convert(
                price, to_currency, order.company_id, fields.Date.today()),
            'date': fields.Date.today(),
            'suggested_products': order._cart_accessories()
        })

        if not display:
            return value

        value['website_sale.cart_lines'] = request.env['ir.ui.view'].render_template("website_sale.cart_lines", {
            'website_sale_order': order,
            # compute_currency deprecated (not used in view)
            'compute_currency': lambda price: from_currency._convert(
                price, to_currency, order.company_id, fields.Date.today()),
            'date': fields.Date.today(),
            'suggested_products': order._cart_accessories()
        })
        value['website_sale.short_cart_summary'] = request.env['ir.ui.view'].render_template(
            "website_sale.short_cart_summary", {
                'website_sale_order': order,
                'compute_currency': lambda price: from_currency._convert(
                    price, to_currency, order.company_id, fields.Date.today()),
            })
        return value

    @http.route()
    def cart(self, access_token=None, revive='', **post):
        order = request.website.sale_get_order()
        if order and order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order()
        values = {}
        if access_token:
            abandoned_order = request.env['sale.order'].sudo().search([('access_token', '=', access_token)], limit=1)
            if not abandoned_order:  # wrong token (or SO has been deleted)
                return request.render('website.404')
            if abandoned_order.state != 'draft':  # abandoned cart already finished
                values.update({'abandoned_proceed': True})
            elif revive == 'squash' or (revive == 'merge' and not request.session[
                'sale_order_id']):  # restore old cart or merge with unexistant
                request.session['sale_order_id'] = abandoned_order.id
                return request.redirect('/shop/cart')
            elif revive == 'merge':
                abandoned_order.order_line.write({'order_id': request.session['sale_order_id']})
                abandoned_order.action_cancel()
            elif abandoned_order.id != request.session[
                'sale_order_id']:  # abandoned cart found, user have to choose what to do
                values.update({'access_token': abandoned_order.access_token})

        if order:
            from_currency = order.company_id.currency_id
            to_currency = order.pricelist_id.currency_id
            compute_currency = lambda price: from_currency._convert(
                price, to_currency, request.env.user.company_id, fields.Date.today())
        else:
            compute_currency = lambda price: price

        values.update({
            'website_sale_order': order,
            'compute_currency': compute_currency,
            'date': fields.Date.today(),
            'suggested_products': [],
        })
        if order:
            _order = order
            if not request.env.context.get('pricelist'):
                _order = order.with_context(pricelist=order.pricelist_id.id)
            values['suggested_products'] = _order._cart_accessories()

        if post.get('type') == 'popover':
            # force no-cache so IE11 doesn't cache this XHR
            return request.render("website_sale.cart_popover", values, headers={'Cache-Control': 'no-cache'})

        if post.get('type') == 'sidecart':
            return request.render("extended_ecommerce.side_cart", values, headers={'Cache-Control': 'no-cache'})

        return request.render("website_sale.cart", values)

    @http.route()
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        if sale_order_id is None:
            order = request.website.sale_get_order()
        else:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            assert order.id == request.session.get('sale_last_order_id')

        if transaction_id:
            tx = request.env['payment.transaction'].sudo().browse(transaction_id)
            assert tx in order.transaction_ids()
        elif order:
            tx = order.get_portal_last_transaction()
        else:
            tx = None

        if not order or (order.amount_total and not tx):
            return request.redirect('/shop')

        if order and not order.amount_total and not tx:
            return request.redirect(order.get_portal_url())

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()
        if tx and tx.state == 'draft':
            return request.redirect('/shop')

        PaymentProcessing.remove_payment_transaction(tx)

        order.message_subscribe(partner_ids=[3], subtype_ids=[1, 7, 8])
        order.message_post(
            body=_('A new order has been placed using %s payment method.') % order.transaction_ids[0].acquirer_id.name,
            partner_ids=[3],
            record_name=order.display_name,
            res_id=order.id,
            model='sale.order',
            subtype_id=1,
            notif_layout='mail.mail_notification_light'
        )
        return request.redirect('/shop/confirmation')


class TableCompute(object):

    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey):
        res = True
        for y in range(sizey):
            for x in range(sizex):
                if posx + x >= PPR:
                    res = False
                    break
                row = self.table.setdefault(posy + y, {})
                if row.setdefault(posx + x) is not None:
                    res = False
                    break
            for x in range(PPR):
                self.table[posy + y].setdefault(x, None)
        return res

    def process(self, products, ppg=PPG):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        x = 0
        for p in products:
            x = min(max(p.website_size_x, 1), PPR)
            y = min(max(p.website_size_y, 1), PPR)
            if index >= ppg:
                x = y = 1

            pos = minpos
            while not self._check_place(pos % PPR, pos // PPR, x, y):
                pos += 1
            # if 21st products (index 20) and the last line is full (PPR products in it), break
            # (pos + 1.0) / PPR is the line where the product would be inserted
            # maxy is the number of existing lines
            # + 1.0 is because pos begins at 0, thus pos 20 is actually the 21st block
            # and to force python to not round the division operation
            if index >= ppg and ((pos + 1.0) // PPR) > maxy:
                break

            if x == 1 and y == 1:   # simple heuristic for CPU optimization
                minpos = pos // PPR

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos // PPR) + y2][(pos % PPR) + x2] = False
            self.table[pos // PPR][pos % PPR] = {
                'product': p, 'x': x, 'y': y,
                'class': " ".join(x.html_class for x in p.website_style_ids if x.html_class)
            }
            if index <= ppg:
                maxy = max(maxy, y + (pos // PPR))
            index += 1

        # Format table according to HTML needs
        rows = sorted(self.table.items())
        rows = [r[1] for r in rows]
        for col in range(len(rows)):
            cols = sorted(rows[col].items())
            x += len(cols)
            rows[col] = [r[1] for r in cols if r[1]]

        return rows
