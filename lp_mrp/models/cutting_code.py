# -*- coding: utf-8 -*-
'''cutting code'''
from odoo import fields, models


class CuttingCode(models.Model):
    '''new model cutting.code'''
    _name = 'cutting.code'
    _description = 'cutting code'

    name = fields.Char('Cutting Code')