import random

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.web import Home
from odoo.exceptions import UserError


class Web(Home):
    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        homepage = request.website.homepage_id
        brand_ids = {}

        categories = request.env['product.public.category'].search([('parent_id', '=', False)])
        sale_order = request.website.sale_get_order()

        if request.session.get('search_keywords_brands'):
            for brand in request.session['search_keywords_brands']:
                brand_ids[brand] = True

        if sale_order:
            for prod in sale_order.website_order_line:
                brand_ids[prod.product_id.brand_id.id] = True
            brand_ids = list(brand_ids)

            suggested = request.env['product.template']._random_products(brand_ids)
        else:
            brand_ids = list(brand_ids)
            suggested = request.env['product.template']._random_products(brand_ids)

        filtered = random.sample(categories, 6)
        top_array = request.env['product.template']._random_products()

        if not request.session.get('show_banner'):
            show_banner = True
            request.session['show_banner'] = True
        else:
            show_banner = False

        if homepage and (homepage.sudo().is_visible or request.env.user.has_group('base.group_user')) and homepage.url != '/':
            values = {
                'featured_products': top_array[:12],
                'top_categories': filtered,
                'categories': categories,
                'suggested': suggested[:12],
                'show_banner': show_banner
            }
            return request.render("website.homepage", values)

        website_page = request.env['ir.http']._serve_page()
        if website_page:
            values = {
                'featured_products': top_array[:12],
                'top_categories': filtered,
                'categories': categories,
                'suggested': suggested[:12],
                'show_banner': show_banner
            }
            return request.render("website.homepage", values)
        else:
            top_menu = request.website.menu_id
            first_menu = top_menu and top_menu.child_id and top_menu.child_id.filtered(lambda menu: menu.is_visible)
            if first_menu and first_menu[0].url not in ('/', '') and (not (first_menu[0].url.startswith(('/?', '/#', ' ')))):
                return request.redirect(first_menu[0].url)

        raise request.not_found()
