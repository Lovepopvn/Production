# -*- coding: utf-8 -*-
'''MRP Workcenter'''
from odoo import fields, models, api, _


class MrpWorkcenter(models.Model):
    '''inherit mrp.workcenter'''
    _inherit = 'mrp.workcenter'

    default_operation = fields.Boolean('Default Operation for Material Consumption', copy=False)
    used_scan_process = fields.Boolean('Pieces Scan Required')
    default_operation_pick = fields.Boolean('Default Operation Pick Paper', copy=False)
    ending_work_center = fields.Boolean('Ending Work center', copy=False)
