# -*- coding: utf-8 -*-
'''Factory Constants LP Machine Flow'''
from odoo import fields, models


class FactoryConstantsLpMachineFlow(models.Model):
    '''new model factory.lp.machine.flow'''
    _name = 'factory.constants.lp.machine.flow'
    _description = 'Factory Constants LP Machine Flow'

    name = fields.Char(string='Machine Flow', required=True)
    code = fields.Char(string='Machine Code', required=True)
