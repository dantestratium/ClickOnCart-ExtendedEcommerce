import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WebsiteSaleEvent(models.Model):
    _name = 'website.sale.event'
    _description = 'Website Sale Events'

    name = fields.Char(string='Name', required=True)
    link = fields.Char(string='Url Link')
    state = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active', required=True)
    product_ids = fields.Many2many('product.template', string='Products')
    date_start = fields.Datetime('Start Date', default=datetime.datetime.now())
    date_end = fields.Datetime('End Date')

    @api.multi
    def generate(self):
        events = []
        result = self.env['website.sale.event'].search([('date_start', '<=', datetime.datetime.now()), ('state', '=', 'active')])

        for event in result:
            if event.date_end:
                if event.date_end >= datetime.datetime.now():
                    event.date_start = datetime.datetime.now()
                    events.append(event)
            else:
                events.append(event)

        return events

