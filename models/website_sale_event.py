import pytz

from datetime import datetime
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
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
    date_start = fields.Datetime('Start Date', default=datetime.now())
    date_end = fields.Datetime('End Date')
    date_end_formatted = fields.Char(string='End Date Formatted')

    @api.multi
    def generate(self):
        events = []
        local = pytz.timezone('Asia/Manila')
        result = self.env['website.sale.event'].search([('date_start', '<=', datetime.now()), ('state', '=', 'active')])

        for event in result:
            if event.date_end:
                if event.date_end >= datetime.now():
                    event.date_start = datetime.now()
                    event.date_end_formatted = datetime.strftime(pytz.utc.localize(
                        datetime.strptime(event.date_end.strftime("%Y-%m-%d %H:%M:%S"), DEFAULT_SERVER_DATETIME_FORMAT))
                                                       .astimezone(local), "%Y-%m-%d %H:%M:%S")
                    events.append(event)
            else:
                events.append(event)

        return events

