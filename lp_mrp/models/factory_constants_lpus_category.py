# -*- coding: utf-8 -*-
'''Factory Constants LP Product Type'''
from odoo import fields, models, _


class FactoryConstantsLpusCategory(models.Model):
    '''new model factory.constants.lpus.category'''
    _name = 'factory.constants.lpus.category'
    _description = 'Factory Constants LPUS Category'

    name = fields.Char(string='LPUS Category', required=True)
    routing_profile_id = fields.Many2one(
        comodel_name='routing.profile', string="Routing Profile")
    allow_proceed_remove_packaging = fields.Boolean(
        string='Allow to proceed the removing packaging data')
    factory_constants_id = fields.Many2one(
        comodel_name='factory.constants', string="Factory Constants")

    def name_get(self):
        result = []
        if self._context.get('show_routing_profile'):
            for lp in self:
                result.append((lp.id, _("%s")%(lp.routing_profile_id.name)))
        else:
            for lp in self:
                result.append((lp.id, _("%s")%(lp.name)))
        return result
