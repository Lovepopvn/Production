# -*- coding: utf-8 -*-
'''routing profile'''
from odoo import fields, models


class RoutingProfile(models.Model):
    '''new model routing.profile'''
    _name = 'routing.profile'
    _description = 'Routing Profile'

    name = fields.Char('Routing Profile')