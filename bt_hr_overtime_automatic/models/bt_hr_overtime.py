# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2018-BroadTech IT Solutions (<http://www.broadtech-innovations.com/>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from odoo import fields, api, models, _
from datetime import date,datetime,timedelta
from ast import literal_eval
import datetime
import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta

class BtHrOvertime(models.Model):   
    _name = "bt.hr.overtime"
    _description = "Bt Hr Overtime" 
    _rec_name = 'employee_id'
    _order = 'id desc'
    
    employee_id = fields.Many2one('hr.employee', string="Employee")
    manager_id = fields.Many2one('hr.employee', string='Manager')
    start_date = fields.Datetime('Date')
    overtime_hours = fields.Float('Overtime Hours')
    notes = fields.Text(string='Notes')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Waiting Approval'), ('refuse', 'Refused'), 
           ('validate', 'Approved'), ('cancel', 'Cancelled')], default='draft', copy=False)
    attendance_id = fields.Many2one('hr.attendance', string='Attendance')
    
    @api.model
    def run_overtime_scheduler(self):
        """ This Function is called by scheduler. """
        current_date = date.today()
        working_hours_empl = self.env['hr.contract']
        attend_signin_ids = self.env['hr.attendance'].search([('overtime_created', '=', False)])
        for obj in attend_signin_ids:
            if obj.check_in and obj.check_out:               
                start_date = datetime.datetime.strptime(obj.check_in.strftime('%Y-%m-%d %H:%M:%S'), DEFAULT_SERVER_DATETIME_FORMAT)                
                end_date = datetime.datetime.strptime(obj.check_out.strftime('%Y-%m-%d %H:%M:%S'), DEFAULT_SERVER_DATETIME_FORMAT)                 
                difference = end_date - start_date
                #To calculate hour difference of an employee. It will calculate hour difference even if employee work more than 24 hours 
                hour_diff =int((difference.days) * 24 + (difference.seconds) / 3600)  
                min_diff = str(difference).split(':')[1]
                tot_diff = str(hour_diff) + '.' + min_diff
                actual_working_hours = float(tot_diff)
                contract_obj = self.env['hr.contract'].search([('employee_id', '=', obj.employee_id.id),('work_hours','!=',0)])
                for contract in contract_obj:
                    working_hours = contract.work_hours
                    if actual_working_hours > working_hours:
                        overtime_hours = actual_working_hours - working_hours
                        vals = {
                            'employee_id':obj.employee_id and obj.employee_id.id or False,
                            'manager_id' : obj.employee_id and obj.employee_id.parent_id and obj.employee_id.parent_id.id or False,
                            'start_date' : obj.check_in,
                            'overtime_hours': round(overtime_hours,2),
                            'attendance_id': obj.id,
                            }
                        self.env['bt.hr.overtime'].create(vals)
                        obj.overtime_created = True
                        
    def action_submit(self):
        return self.write({'state':'confirm'})
            
    def action_cancel(self):
        return self.write({'state':'cancel'})
            
    def action_approve(self):
        return self.write({'state':'validate'})
        
    def action_refuse(self):
        return self.write({'state':'refuse'})
            
    def action_view_attendance(self):
        attendances = self.mapped('attendance_id')
        action = self.env.ref('hr_attendance.hr_attendance_action').read()[0]
        if len(attendances) > 1:
            action['domain'] = [('id', 'in', attendances.ids)]
        elif len(attendances) == 1:
            action['views'] = [(self.env.ref('hr_attendance.hr_attendance_view_form').id, 'form')]
            action['res_id'] = self.attendance_id.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
        

class Contract(models.Model):
    _inherit = 'hr.contract'
    
    work_hours = fields.Float(string='Working Hours')
    
    
class HrAttendance(models.Model):
    _inherit = "hr.attendance" 
    
    overtime_created = fields.Boolean(string = 'Overtime Created', default=False, copy=False)
    
