# -*- coding: utf-8 -*-
'''Picking Wave'''
import json

from odoo import fields, models, api, _


class PickingWave(models.Model):
    '''new model picking.wave'''
    _name = 'picking.wave'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Picking Wave'

    name = fields.Char('Picking Wave Name', default=lambda self: self.env['ir.sequence'].next_by_code('picking.wave'))
    priority = fields.Selection([
        ('very_urgent', 'Very Urgent'),
        ('urgent', 'Urgent'),
        ('priority', 'Priority'),
        ('standard', 'Standard')
        ], string='Priority', tracking=True, copy=False)
    carrier_id = fields.Many2one("delivery.carrier", string="Carrier/Service")
    tracking_number = fields.Char('Tracking Number')
    shipment_method = fields.Selection([
        ('AIR', 'Air'),
        ('SEA', 'SEA'),
        ('LCL', 'LCL')
        ], string ='Shipment Method', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('planned', 'Planned'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='State', tracking=True, default='draft')
    shipping_status = fields.Selection([
        ('waiting', 'Waiting'),
        ('assigned', 'Assigned'),
        ('shipped', 'Shipped'),
        ('received', 'Received')
    ], string="Shipping Status", tracking=True)
    product_lot_ids = fields.One2many(
        comodel_name='product.lot', inverse_name='picking_wave_id',
        string='Packaging Definition', copy=False)
    delivery_order_ids = fields.One2many(
        comodel_name='stock.picking', inverse_name='wave_id',
        string='Delivery Definition', copy=False)    
    weight = fields.Float('Weight')
    master_tracking_reference = fields.Char(string='Master tracking Reference')
    total_product_lot = fields.Integer(string='Total Number of boxes')
    commercial_invoice = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'picking.wave')], string='Commercial Invoice')
    custom_declaration = fields.Char(string='Custom Declaration')
    carrier_price = fields.Float(string="Shipping Cost")
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, index=True)
    carrier_tracking_url = fields.Char(string='Tracking URL', compute='_compute_carrier_tracking_url')
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', check_company=True,  # Unrequired company
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Pricelist for shipping item.")
    tracking_url = fields.Char(string='Tracking Link')

    @api.depends('tracking_number')
    def _compute_carrier_tracking_url(self):
        for wave in self:
            if wave.product_lot_ids:
                carrier_id = wave.product_lot_ids[0].carrier_id
                wave.carrier_tracking_url = carrier_id.fedex_wave_get_tracking_link(wave) if carrier_id and wave.tracking_number else False
            else:
                wave.carrier_tracking_url = False

    def button_confirm(self):
        for wave in self:
            wave.state = 'progress'
            wave.shipping_status = 'assigned'
    
    def validate_so(self, delivery_order):
        pick_to_do = self.env['stock.picking']
        for picking in delivery_order:
            # If still in draft => confirm and assign
            if picking.state == 'draft':
                picking.action_confirm()
                if picking.state != 'assigned':
                    picking.action_assign()
                    if picking.state != 'assigned':
                        raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
            for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                for move_line in move.move_line_ids:
                    move_line.qty_done = move_line.product_uom_qty
            pick_to_do |= picking
        if pick_to_do:
            pick_to_do.action_done()

    def send_to_shipper(self):
        self.ensure_one()
        res = self.carrier_id.send_shipping_wave(self)[0]
        '''check'''
        if self.carrier_id.free_over and self.sale_id and self.sale_id._compute_amount_total_without_delivery() >= self.carrier_id.amount:
            res['exact_price'] = 0.0
        self.carrier_price = res['exact_price'] * (1.0 + (self.carrier_id.margin / 100.0))
        if res['tracking_number']:
            self.tracking_number = res['tracking_number']
        tracking_number = tuple(res['tracking_number'].split(','))
        n = 0
        for lot in self.product_lot_ids:
            lot.tracking_number = tracking_number[n]
            n += 1
        sale_currency = self.product_lot_ids[0].mo_id.sale_id.currency_id
        order_currency = sale_currency or self.company_id.currency_id
        msg = _("Shipment sent to carrier %s for shipping with tracking number %s<br/>Cost: %.2f %s") % (self.carrier_id.name, self.tracking_number, self.carrier_price, order_currency.name)
        self.message_post(body=msg)
        '''check'''
        # self._add_delivery_cost_to_so()

    def _send_confirmation_email(self):
        for shipping in self:
            if shipping.carrier_id:
                if shipping.carrier_id.integration_level == 'rate_and_ship':
                    shipping.send_to_shipper()

        
    def button_validate(self):
        for wave in self:
            wave.state = 'done'
            wave.shipping_status = 'shipped'
            wave.validate_so(wave.delivery_order_ids)
            wave._send_confirmation_email()

    def open_website_url(self):
        self.ensure_one()
        if not self.carrier_tracking_url:
            raise UserError(_("Your delivery method has no redirect on courier provider's website to track this order."))

        carrier_trackers = []
        try:
            carrier_trackers = json.loads(self.carrier_tracking_url)
        except ValueError:
            carrier_trackers = self.carrier_tracking_url
        else:
            msg = "Tracking links for shipment: <br/>"
            for tracker in carrier_trackers:
                msg += '<a href=' + tracker[1] + '>' + tracker[0] + '</a><br/>'
            self.message_post(body=msg)
            return self.env.ref('delivery.act_delivery_trackers_url').read()[0]

        client_action = {
            'type': 'ir.actions.act_url',
            'name': "Shipment Tracking Page",
            'target': 'new',
            'url': self.carrier_tracking_url,
        }
        return client_action
