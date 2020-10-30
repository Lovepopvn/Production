# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class CancelSo(models.TransientModel):
    _name = 'cancel.so'
    _description = 'Cancel SO with related MO'

    name = fields.Char()
    description = fields.Text()
    sale_id = fields.Many2one('sale.order', 'Sale Order')

    @api.model
    def default_get(self, fields):
        """ get default value """
        res = super(CancelSo, self).default_get(fields)
        if self._context and self._context.get('active_id'):
            sale_obj = self.env['sale.order']
            sale_id = sale_obj.browse(self._context['active_id'])
            desc = "This Sale Order related with MO %s. \nDo you want to still cancel it?" % sale_id.manufacturing_order
            res['description'] = desc
            res['sale_id'] = sale_id.id
        return res
    
    def action_cancel(self):
        self.sale_id.action_cancel()
