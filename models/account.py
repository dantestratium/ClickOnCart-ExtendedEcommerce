from odoo import api, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.multi
    def action_validate_invoice_payment(self):
        res = super(AccountPayment, self).action_validate_invoice_payment()
        for payment in self:
            for invoice in payment.invoice_ids:
                for line in invoice.invoice_line_ids:
                    for sale_line in line.sale_line_ids:
                        sale_line.order_id.status_desc = 'done'
        return res
