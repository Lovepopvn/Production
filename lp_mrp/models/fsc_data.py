# -*- coding: utf-8 -*-
'''FSC Status'''
from odoo import fields, models


class FscStatus(models.Model):
    '''new model fsc.status'''
    _name = 'fsc.status'
    _description = 'FSC Status'

    name = fields.Char('FSC Status')

class FscGroup(models.Model):
    '''new model fsc.group'''
    _name = 'fsc.group'
    _description = 'FSC Group'

    name = fields.Char('FSC Group')