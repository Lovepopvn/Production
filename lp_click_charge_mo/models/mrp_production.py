# -*- coding: utf-8 -*-
'''Manufacturing Order'''
from odoo import fields, models, api


class MrpProduction(models.Model):
    '''inherit mrp.production'''
    _inherit = 'mrp.production'

    average_click_charge_when_done = fields.Float(compute='_compute_click_cost', store=True)

    @api.depends('state')
    def _compute_click_cost(self):
        for record in self:
            if record.state == 'done' and record.average_click_charge_when_done == 0.0 and record.company_id and record.company_id.factory_constants_id:
                factory_constants = record.company_id.factory_constants_id
                record.average_click_charge_when_done = factory_constants.average_click_charge
            else:
                record.average_click_charge_when_done = 0.0
