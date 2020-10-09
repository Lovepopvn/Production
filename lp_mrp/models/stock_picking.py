# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    wave_id = fields.Many2one('picking.wave', 'Picking Wave', copy="False")
    deliver_document_update = fields.Boolean()

class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.onchange('product_id', 'picking_type_id')
    def onchange_product(self):
        res = super(StockMove, self).onchange_product_id()
        if self.product_id:
            if self.product_id.fsc_group_id or self.product_id.fsc_status_id:
                if self.product_id.fsc_group_id and self.product_id.fsc_status_id:
                    self.name = ' - ' + self.product_id.fsc_group_id.name + ' ' + self.product_id.fsc_status_id.name
                elif self.product_id.fsc_group_id and not self.product_id.fsc_status_id:
                    self.name = ' - ' + self.product_id.fsc_group_id.name
                elif not self.product_id.fsc_group_id and self.product_id.fsc_status_id:
                    self.name = ' - ' + self.product_id.fsc_status_id.name