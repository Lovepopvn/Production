# -*- coding: utf-8 -*-
'''Product Configuration'''
from odoo import fields, models


class LpProductCategory(models.Model):
    '''new model lp.product.category'''
    _name = 'lp.product.category'
    _description = 'LP Product Category'

    name = fields.Char(string='LP Product Categories', required=True)


class LpProductBrand(models.Model):
    '''new model lp.product.brand'''
    _name = 'lp.product.brand'
    _description = 'LP Product Brand'

    name = fields.Char(string='Product Brand', required=True)


class ProductCategory(models.Model):
    '''new model product.category'''
    _inherit = 'product.category'

    production_information = fields.Boolean(string='Production information')
