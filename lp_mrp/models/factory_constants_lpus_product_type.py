# -*- coding: utf-8 -*-
'''Factory Constants LP Manufacturing Type'''
from odoo import fields, models


class FactoryConstantsLpusProductType(models.Model):
    '''new model factory.constants.lpus.product.type'''
    _name = 'factory.constants.lpus.product.type'
    _description = 'Factory Constants LPUS Product Type'

    name = fields.Char(string='LPUS Product Type', required=True)
    default_hts_code = fields.Char(string='Default HTS Code')
    factory_constants_id = fields.Many2one(
        comodel_name='factory.constants', string="Factory Constants")
    allow_proceed_remove = fields.Boolean(string="Allow to proceed the Removing Packaging  of Child MO")
