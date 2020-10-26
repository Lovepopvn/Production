# -*- coding: utf-8 -*-
'''Licensed Brand'''
from odoo import fields, models


class LicensedBrand(models.Model):
    '''new model licensed.brand'''
    _name = 'licensed.brand'
    _description = 'Licensed Brand'

    name = fields.Char('Licensed Brand')