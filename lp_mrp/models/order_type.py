# -*- coding: utf-8 -*-
'''Order Type'''
from odoo import fields, models


class OrderType(models.Model):
    '''new model order.type'''
    _name = 'order.type'
    _description = 'Order Type'

    name = fields.Char('Order Type')