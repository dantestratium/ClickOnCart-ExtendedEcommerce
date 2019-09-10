import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WebsiteBanner(models.Model):
    _name = 'website.banner'
    _description = 'Website Banners'
    _order = 'sequence'

    name = fields.Char(string='Name', required=True)
    url = fields.Binary(string='Banner Image', required=True)
    link = fields.Text(string='Url Link')
    type = fields.Selection([
        ('web', 'Website'),
        ('mobile', 'Mobile'),
        ('side', 'Side')
    ], string='Placement', default='web', required=True)
    state = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active', required=True)
    date_start = fields.Datetime('Start Date', default=datetime.datetime.now())
    date_end = fields.Datetime('End Date')
    sequence = fields.Integer(string='Sequence', default=0)


    @api.multi
    def generate(self, bannertype='web'):
        banners = []
        result = self.env['website.banner'].search([('type', '=', bannertype), ('date_start', '<=', datetime.datetime.now()), ('state', '=', 'active')])

        for banner in result:
            if banner.date_end:
                if banner.date_end >= datetime.datetime.now():
                    banners.append(banner)
            else:
                banners.append(banner)

        return banners
