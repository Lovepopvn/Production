# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from datetime import datetime


class DoRemoveWave(models.TransientModel):
    _name = 'do.remove.wave'
    _description = 'Wizard to confirm remove DO from pickingwave'

    name = fields.Char()
    description = fields.Text()
    picking_id = fields.Many2one('stock.picking', 'Delivery Order')
    
    def action_confirm(self):
        product_lot_ids = self.env['product.lot'].search([('delivery_order_id', '=', self.picking_id.id)])
        query = """
                    update product_lot set picking_wave_id = null, tracking_number = null, shipper_reference = null, create_date = '%s'
                    where id in %s
                        """ % (datetime.now(),tuple(product_lot_ids.ids))
        self._cr.execute(query)
        self.picking_id.write({'wave_id': False})
