# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class MoDivisible(models.TransientModel):
    _name = 'mo.divisible'
    _description = 'Wizard to confirm MO divisible qty'

    name = fields.Char()
    description = fields.Text()
    sale_id = fields.Many2one('sale.order', 'Sale Order')

    # @api.model
    # def default_get(self, fields):
    #     """ get default value """
    #     res = super(MoDivisible, self).default_get(fields)
    #     if self._context and self._context.get('active_id'):
    #         # sale_obj = self.env['sale.order']
    #         # sale_id = sale_obj.browse(self._context['active_id'])
    #         desc = "Manufacturing Order Quantity can not less than Batch Size"
    #         res['description'] = desc
    #         # res['sale_id'] = sale_id.id
    #     return res
    
    def action_confirm(self):
        self.sale_id.with_context(pass_confirm=True).action_confirm()
