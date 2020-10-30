# -*- coding: utf-8 -*-
'''Factory Constants LP Product Packaging'''
from odoo import fields, models


class FactoryConstantsLpProductPackaging(models.Model):
    '''new model factory.constants.lp.product.packaging'''
    _name = 'factory.constants.lp.product.packaging'
    _description = 'Factory Constants LP Product Packaging'
    _rec_name = 'product_id'

    lpus_product_type_id = fields.Many2one(
        comodel_name='factory.constants.lpus.product.type',
        string='LPUS Product Type', required=True)
    lpus_category_id = fields.Many2one(
        comodel_name='factory.constants.lpus.category',
        string='LPUS Category', required=True)
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product', required=True)
    quantity = fields.Integer(string='Quantity per product')
    card_unit = fields.Float(string='Card for units')
    factory_constants_id = fields.Many2one(
        comodel_name='factory.constants', string="Factory Constants")
    packaging_data_removable = fields.Boolean(
        string='Packaging Data Removable')
