# -*- coding: utf-8 -*-
{
    'name': 'Extended Ecommerce',
    'version': '1.0',
    'category': 'API',
    'sequence': 1,
    'summary': 'Extended most of e-commerce/website related functionalities',
    'description': "",
    'author': "Stratium Software Group",
    'website': "http://www.stratiumsoftware.com",
    'depends': [
        'website_sale',
        'auth_oauth',
        'website_sale_delivery',
        'login_page'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account.xml',
        'views/payment.xml',
        'views/sale.xml',
        'views/sale_event.xml',
        'views/sale_management.xml',
        'views/banner.xml',
        'views/brand.xml',
        'views/product.xml',
        'views/res.xml',
        'views/stock.xml',
        'templates/account.xml',
        'templates/payment.xml',
        'templates/portal.xml',
        'templates/sale.xml',
        'templates/template.xml',
        'templates/web.xml',
        'templates/website.xml',
        'templates/website_sale.xml',
        'templates/website_sale_wishlist.xml'
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True
}