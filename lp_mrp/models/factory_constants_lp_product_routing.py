# -*- coding: utf-8 -*-
'''Factory Constants LP Product Routing'''
from odoo import fields, models


class FactoryConstantsLpProductRouting(models.Model):
    '''new model factory.constants.lp.product.routing'''
    _name = 'factory.constants.lp.product.routing'
    _description = 'Factory Constants LP Product Routing'
    _rec_name = 'routing_profile_id'

    routing_profile_id = fields.Many2one(
        comodel_name='routing.profile',
        string='Routing Profile', required=True)
    routing_id = fields.Many2one(
        comodel_name='mrp.routing', string='Routing', required=True)
    factory_constants_id = fields.Many2one(
        comodel_name='factory.constants', string="Factory Constants")
