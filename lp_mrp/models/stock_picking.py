# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    wave_id = fields.Many2one('picking.wave', 'Picking Wave', copy="False")
    deliver_document_update = fields.Boolean()

    def remove_do(self):
        for pick in self:
            view = self.env.ref('lp_mrp.do_remove_wave_wizard_view')
            desc = "Reset will bring the DO and its product lot to ready to shipped stage, \nDo you want to continue?"
            wiz = self.env['do.remove.wave'].create({'picking_id': pick.id,
                                                    'description': desc})
            return {
                'name': _('Delivery Order Remove Confirmation'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'do.remove.wave',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

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