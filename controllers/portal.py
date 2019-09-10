from odoo.http import request
from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class ExtendCustomerPortal(CustomerPortal):
    def _prepare_portal_layout_values(self):
        values = super(ExtendCustomerPortal, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        SaleOrder = request.env['sale.order']
        to_ship_count = SaleOrder.search_count([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('status_desc', '=', 'delivery'),
            ('state', '=', 'sale')
        ])
        to_confirm_count = SaleOrder.search_count([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['draft', 'sent'])
        ])
        to_receive_count = SaleOrder.search_count([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('status_desc', 'in', ['delivered', 'received'])
        ])
        cancelled = SaleOrder.search_count([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', '=', 'cancel')
        ])

        values.update({
            'to_ship_count': to_ship_count,
            'to_receive_count': to_receive_count,
            'to_confirm_count': to_confirm_count,
            'cancelled_count': cancelled
        })

        return values

    @http.route(['/my/confirm', '/my/confirm/page/<int:page>'], type='http', auth="user", website=True)
    def portal_to_confirm_order(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', '=', 'sent')
        ]

        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }

        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('sale.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        quotation_count = SaleOrder.search_count(domain)
        pager = portal_pager(
            url="/my/confirm",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=quotation_count,
            page=page,
            step=self._items_per_page
        )

        quotations = SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_quotations_history'] = quotations.ids[:100]

        values.update({
            'date': date_begin,
            'orders': quotations.sudo(),
            'page_name': 'quote',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/confirm',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })

        return request.render("extended_ecommerce.portal_to_confirm_orders", values)

    @http.route(['/my/cancelled', '/my/cancelled/page/<int:page>'], type='http', auth="user", website=True)
    def portal_cancelled_order(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', '=', 'cancel')
        ]

        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }

        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('sale.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        quotation_count = SaleOrder.search_count(domain)
        pager = portal_pager(
            url="/my/cancelled",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=quotation_count,
            page=page,
            step=self._items_per_page
        )

        orders = SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_cancelled_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders.sudo(),
            'page_name': 'cancelled',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/cancelled',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })

        return request.render("extended_ecommerce.portal_cancelled_orders", values)

    @http.route(['/my/ship', '/my/ship/page/<int:page>'], type='http', auth="user", website=True)
    def portal_to_ship_order(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', '=', 'sale'),
            ('status_desc', '=', 'delivery')
        ]

        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }

        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('sale.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        order_count = SaleOrder.search_count(domain)
        pager = portal_pager(
            url="/my/ship",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=order_count,
            page=page,
            step=self._items_per_page
        )
        orders = SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_orders_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders.sudo(),
            'page_name': 'order',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/ship',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })

        return request.render("extended_ecommerce.portal_to_ship_orders", values)

    @http.route(['/my/receive', '/my/receive/page/<int:page>'], type='http', auth="user", website=True)
    def portal_to_receive_order(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('status_desc', 'in', ['delivered', 'received'])
        ]

        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }

        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('sale.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        order_count = SaleOrder.search_count(domain)
        pager = portal_pager(
            url="/my/receive",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=order_count,
            page=page,
            step=self._items_per_page
        )

        orders = SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_orders_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders.sudo(),
            'page_name': 'order',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/receive',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })

        return request.render("extended_ecommerce.portal_to_receive_orders", values)

    @http.route(['/my/orders/<int:order_id>/cancel'], type='http', auth="public", methods=['POST'], website=True)
    def decline(self, order_id, access_token=None, **post):
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        query_string = False
        if order_sudo.status_desc in ('confirm', 'delivery'):
            order_sudo.action_cancel()

        return request.redirect(order_sudo.get_portal_url(query_string=query_string))
