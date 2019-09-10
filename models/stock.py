from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('delivery', 'On Delivery'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, track_visibility='onchange',
        help=" * Draft: not confirmed yet and will not be scheduled until confirmed.\n"
             " * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows).\n"
             " * Waiting: if it is not ready to be sent because the required products could not be reserved.\n"
             " * Ready: products are reserved and ready to be sent. If the shipping policy is 'As soon as possible' this happens as soon as anything is reserved.\n"
             " * Done: has been processed, can't be modified or cancelled anymore.\n"
             " * Cancelled: has been cancelled, can't be confirmed anymore.")

    @api.multi
    def action_done(self):
        if not self.partner_id.is_delivery_partner:
            raise UserError(_('Please edit and select the Partner to deliver the order.'))

        if self.sale_id.status_desc == 'delivery':
            self.sale_id.status_desc = 'delivered'
            self.partner_id.delivery_count += 1
            self.state = 'delivery'

            return True

        todo_moves = self.mapped('move_lines').filtered(lambda self: self.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])

        for pick in self:
            for ops in pick.move_line_ids.filtered(lambda x: not x.move_id):
                moves = pick.move_lines.filtered(lambda x: x.product_id == ops.product_id)
                moves = sorted(moves, key=lambda m: m.quantity_done < m.product_qty, reverse=True)
                if moves:
                    ops.move_id = moves[0].id
                else:
                    new_move = self.env['stock.move'].create({
                        'name': _('New Move:') + ops.product_id.display_name,
                        'product_id': ops.product_id.id,
                        'product_uom_qty': ops.qty_done,
                        'product_uom': ops.product_uom_id.id,
                        'location_id': pick.location_id.id,
                        'location_dest_id': pick.location_dest_id.id,
                        'picking_id': pick.id,
                        'picking_type_id': pick.picking_type_id.id,
                       })
                    ops.move_id = new_move.id
                    new_move._action_confirm()
                    todo_moves |= new_move
        todo_moves._action_done()

        self.write({'date_done': fields.Datetime.now()})
        self.sudo().sale_id.is_delivered = True
        self.sudo().sale_id.status_desc = 'received'
        self.sudo().sale_id.state = 'done'

        return True
