# -*- coding: utf-8 -*-
'''Product Lot'''
from odoo import fields, models, api, _
from odoo.exceptions import Warning
from datetime import datetime
from pytz import timezone


class ProductLot(models.Model):
    '''new model product.lot'''
    _name = 'product.lot'
    _inherit = ['barcodes.barcode_events_mixin']
    _description = 'Product Lot'
    _order = 'write_date DESC'

    name = fields.Char('Product Lot', default="/", copy=False)
    state = fields.Selection([
        ('not_received', 'Not Received'),
        ('received', 'Received'),
        ('verified', 'Verified'),
        ('accounted_for', 'Accounted For')
        ], string='State', copy=False)
    delivery_order_id = fields.Many2one('stock.picking', 'Delivery order', copy="False")
    mo_id = fields.Many2one('mrp.production', 'Manufacturing Order', copy="False")
    product_id = fields.Many2one('product.product', 'Product', copy="False")
    # expected_delivery_date = fields.Datetime('Expected Delivery Date')
    tracking_number = fields.Text('Tracking Number')
    tracking_link = fields.Text('Tracking Link')
    picking_wave_id = fields.Many2one('picking.wave', 'Picking Wave')
    create_date = fields.Datetime('Create Date')
    do_ship_date = fields.Datetime('DO Ship Date')
    shipper_reference = fields.Char('Shipper Reference')

    number_of_items = fields.Integer('Number of Items')
    number_of_inner = fields.Integer('Number of Inner')
    inner_per_outer = fields.Integer('Inner per Outer')
    items_per_inner_carton = fields.Integer('Items per Inner Carton')
    sequence_number = fields.Integer('Sequence Number')
    sequence_total = fields.Integer('Sequence Total')
    unit_weight = fields.Float('Unit Weight (kg)')
    unit_price = fields.Float('Unit Price (USD)')
    loaded_container_length = fields.Float('Loaded Container Length (cm)')
    loaded_container_width = fields.Float('Loaded Container Width (cm)')
    loaded_container_height = fields.Float('Loaded Container Height (cm)')
    loaded_container_weight = fields.Float('Loaded Container Weight (kg)')
    scanning_order = fields.Integer('Scanning Order')
    inner_type = fields.Selection([
        ('standard', 'Standard'),
        ('wedding_sample', 'Wedding Sample'),
        ('collectors_box', 'Collectors Box'),
        ('centerpiece_box', 'Centerpiece Box')
        ], string='Inner Type', copy=False)
    received = fields.Integer('Received')
    urgency = fields.Selection([
        ('very_urgent', 'Very Urgent'),
        ('urgent', 'Urgent'),
        ('priority', 'Priority'),
        ('standard', 'Standard')
        ], string='Urgency', copy=False)
    shipment_method = fields.Selection([
        ('AIR', 'Air'),
        ('SEA', 'SEA'),
        ('LCL', 'LCL')
        ], string ='Shipment Method')
    carrier_id = fields.Many2one("delivery.carrier", string="Carrier/Service")
    ready_to_shipped = fields.Boolean(string="Ready to Shipped", default=False)
    packaging_id = fields.Many2one("product.packaging", string="Package Type")
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, index=True)
    brightpearl_warehouse_id = fields.Char('Brightpearl Warehouse ID', copy=False)
    so_number = fields.Char('SO Number', copy=False)
    pallet = fields.Char('Pallet ID', copy=False)
    partner_id = fields.Many2one('res.partner', 'Shipping Address', copy=False)
    mo_for_samples = fields.Boolean('MO for Samples')

    _sql_constraints = [
        ('name_company_uniq', 'unique (name, company_id)', 'Product Lot Reference must be unique per company!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('product.lot') or '/'
        return super(ProductLot, self).create(vals)

    @api.onchange('mo_id')
    def _onchange_mo_id(self):
        if self.mo_id:
            if self.mo_id.mo_for_samples:
                self.mo_for_samples = self.mo_id.mo_for_samples

    def check_address_and_shipment(self):
        delivery_address = False
        shipment_method = False
        for data in self:
            # warning when delivery address in related DO Lot is False
            if not data.delivery_order_id.partner_id.id:
                raise Warning('Please select delivery address in related DO')
            # warning if shipment method in lot is not set
            if not data.shipment_method:
                raise Warning('Please select shipment method in product lot')

            # set variable delivery_address & shipment_method with first value of data to compare with other lot data
            if not delivery_address:
                delivery_address = data.delivery_order_id.partner_id.id
            if not shipment_method:
                shipment_method = data.shipment_method

            # warning if delivery address in related DO or shipment method Lot is not same
            if delivery_address != data.delivery_order_id.partner_id.id:
                raise Warning('Please select product lot with same delivery address')
            elif shipment_method != data.shipment_method:
                raise Warning('Please select product lot with same shipment method')
    
    def check_mo_lot(self):
        lot_ships = self._context.get('active_ids')
        for lot in self:
            lot_same_mo = self.search([('mo_id', '=', lot.mo_id.id)])
            lot_ready_ship = self.search([('mo_id', '=', lot.mo_id.id),
                                          ('id', 'in', lot_ships)])
            if len(lot_same_mo) != len(lot_ready_ship) and not lot.mo_for_samples:
                raise Warning('There are missing product lots detected !! \n'
                                'Please select all product lot created from same Manufacturing Order')
    
    def check_do_lot(self):
        lot_ships = self._context.get('active_ids')
        for lot in self:
            lot_same_do = self.search([('delivery_order_id', '=', lot.delivery_order_id.id)])
            lot_ready_ship = self.search([('delivery_order_id', '=', lot.delivery_order_id.id),
                                          ('id', 'in', lot_ships)])
            if len(lot_same_do) != len(lot_ready_ship) and not lot.mo_for_samples:
                raise Warning('There are missing product lots detected !! \n'
                                'Please select all product lot created from same Delivery Order') 

    def create_shipping_wave(self):
        picking_wave_obj = self.env['picking.wave']
        priority = False
        carrier_id = self[0].carrier_id
        shipment_method = False
        delivery_ids = []
        weight = 0.0
        for data in self:
            deliver_id = data.delivery_order_id
            if deliver_id:
                if deliver_id.id not in delivery_ids:
                    delivery_ids.append(deliver_id.id)
            priority = data.urgency
            if data.carrier_id:
                if carrier_id != data.carrier_id:
                    raise Warning('The assigned carrier is not consistent among the product lots')
                carrier_id = data.carrier_id
            shipment_method = data.shipment_method
            weight += data.loaded_container_weight
            if not data.ready_to_shipped:
                raise Warning('Product Lot is not ready. Please scan first the Product lot')
            if data.picking_wave_id:
                raise Warning('Picking Wave %s already generate for this lot (%s)' % (data.picking_wave_id.name, data.name))
        self.check_address_and_shipment()
        self.check_mo_lot()
        self.check_do_lot()

        # function to generate picking wave name
        tz = timezone("Asia/Ho_Chi_Minh")
        date_formatted = tz.localize(datetime.now()).strftime("%d%m%y")
        shipping_wave_name_format = "VN{}E{}"
        shipping_wave_name = False
        count = 1
        already_exist = True
        while already_exist is True:
            shipping_wave_name = shipping_wave_name_format.format(date_formatted, count)
            already_exist = picking_wave_obj.search_count([["name", "=", shipping_wave_name]]) != 0
            count += 1
        
        wave = picking_wave_obj.create({
            'name': shipping_wave_name,
            'shipping_status': 'waiting',
            'priority': priority,
            'weight': weight,
            'carrier_id': carrier_id.id,
            'shipment_method': shipment_method,
            'total_product_lot': len(self),
        })
        shipped_lot_ids = self.search([('id', 'in', self._context.get('active_ids'))])
        if shipped_lot_ids:
            for ship_lot in shipped_lot_ids:
                ship_lot.picking_wave_id = wave.id
                ship_lot.shipper_reference = f'{wave.name} {ship_lot.name}'
            # shipped_lot_ids.write({'picking_wave_id': wave.id})
        delivery_order_ids = self.env['stock.picking'].search([('id', 'in', delivery_ids)])
        if delivery_order_ids:
            delivery_order_ids.write({'wave_id': wave.id})
        view = self.env.ref('lp_mrp.picking_wave_form_view')
        return {
            'name': _('Mo Divisible Confirmation'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'picking.wave',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'current',
            'res_id': wave.id,
            'context': self.env.context,
        }

    def set_ready_shipped(self):
        for lot in self:
            lot.ready_to_shipped = True
    
    def remove_shipped(self):
        for lot in self:
            lot.ready_to_shipped = False

    @api.model
    def get_barcode_info(self, barcode=False):
        """
        Function called from js to return the required info
        """
        product = self.search(
            [('name', '=', barcode)], limit=1)
        if product:
            if product.ready_to_shipped and not product.picking_wave_id:
                raise Warning(_('This product %(name)s is already to ship') % {'name': product.name})
            elif  product.ready_to_shipped and product.picking_wave_id:
                delivery = ''
                if product.delivery_order_id:
                    delivery = product.delivery_order_id.name
                raise Warning(_('This container belongs to a delivery order %(delivery)s that is already in a picking wave %(wave_id)s') % {'wave_id': product.picking_wave_id.name, 'delivery':delivery})
            else:
                product.write({
                    'ready_to_shipped': True,
                })
                return True
        else:
            return False
