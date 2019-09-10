from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_delivered = fields.Boolean('Is Delivered', default=False)
    status_desc = fields.Selection([
        ('confirm', 'Awaiting Confirmation'),
        ('delivery', 'Awaiting Delivery'),
        ('delivered', 'Order is out for delivery.'),
        ('received', 'Order has been delivered. Awaiting payment to be registered.'),
        ('done', 'Payment confirmed. Order completed.'),
        ('cancel', 'Customer failed to pick up order. Order cancelled.')
    ], string='Order Status', default='confirm')

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            order.status_desc = 'delivery'
        return res

    @api.multi
    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        for order in self:
            order.status_desc = 'cancel'
        return res
