# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from datetime import datetime


class WorkorderPauseReason(models.TransientModel):
    _name = 'workorder.pause.reason'
    _description = 'Reason for Workorder Pause'

    name = fields.Char()
    workorder_id = fields.Many2one('mrp.workorder', 'Workorder')
    wo_productivity_id = fields.Many2one('mrp.workcenter.productivity', 'Productivity')

    @api.model
    def default_get(self, fields):
        """ get default value """
        res = super(WorkorderPauseReason, self).default_get(fields)
        if self._context and self._context.get('active_id'):
            workorder_obj = self.env['mrp.workorder']
            workorder_id = workorder_obj.browse(self._context['active_id'])
            res['workorder_id'] = workorder_id.id
        return res
    
    def action_save(self):
        if self.workorder_id:
            print("SSSS")
        else:
            self.date_end = datetime.now()
            self.wo_productivity_id.write({'note': self.name,
                                            'date_end': datetime.now()})
