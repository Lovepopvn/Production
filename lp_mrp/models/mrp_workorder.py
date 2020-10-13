# -*- coding: utf-8 -*-
'''Mrp Work Order'''
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime
from odoo.tests.common import Form



class MrpWorkOrder(models.Model):
    '''inherit mrp.workorder'''
    _inherit = 'mrp.workorder'

    producing_pieces_parallel = fields.Boolean('Allow producing pieces in parallel', default=True)
    time_progress_ids = fields.One2many(
        'mrp.workcenter.productivity', 'workorder_id', domain=[('date_end','=', False)])
    time_done_ids = fields.One2many(
        'mrp.workcenter.productivity', 'workorder_id', domain=[('date_end','!=', False)])
    pieces_done = fields.Integer()
    
    def open_tablet_view(self):
        self.ensure_one()
        if not self.workcenter_id.used_scan_process:
            if not self.is_user_working and self.working_state != 'blocked':
                self.button_start()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'views': [[self.env.ref('mrp_workorder.mrp_workorder_view_form_tablet').id, 'form']],
            'res_id': self.id,
            'target': 'fullscreen',
            'flags': {
                'withControlPanel': False,
                'form_view_initial_mode': 'edit',
            },
        }
    
    def check_parallel(self, workorder):
        if not self.producing_pieces_parallel:
            productivity_obj = self.env['mrp.workcenter.productivity']
            productivity_ids = productivity_obj.search([('workorder_id', '=', workorder),
                                                    ('date_end', '=', False)])
            if productivity_ids:
                raise UserError(_('This work order is not designed for parallel processing, please finish the in-progress product first'))

    def on_barcode_scanned(self, barcode):
        res = super(MrpWorkOrder, self).on_barcode_scanned(barcode)
        if barcode:
            productivity_obj = self.env['mrp.workcenter.productivity']
            code_obj = self.env['cutting.code']
            workorder_id = self.env.context.get('active_id')
            data = tuple(barcode.split('_'))
            pieces = False
            command = False
            pieces_to_done = self.pieces_done
            if data and len(data) > 1:
                workcenter_tab_obj = self.env['workcenter.tab']
                workcenter_tab_ids = workcenter_tab_obj.search([
                                    ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
                                    ('parallel_workcenter_id', '=', self.workcenter_id.id)
                                    ])
                pieces_done = []
                if workcenter_tab_ids:
                    for workcenter in workcenter_tab_ids:
                        pieces_done.append(workcenter.code_id.id)
                
                if data[0]:
                    pieces = data[0]
                code_id = code_obj.search([('name', '=', pieces)], limit=1)
                if code_id:
                    if code_id.id not in pieces_done:
                        raise UserError(_("You scanned an invalid piece for the current work order."))
                if data[1]:
                    command = data[1]
                if command == 'start':
                    if self.state != 'progress':
                        start_date = datetime.now()
                        query_update = f"""UPDATE mrp_workorder
                            SET state = 'progress', date_start = '{start_date}', date_planned_start = '{start_date}'
                            WHERE id = {workorder_id}
                            """
                        self.env.cr.execute(query_update)
                        if self.date_planned_finished < start_date:
                            query_update = f"""UPDATE mrp_workorder
                                SET date_planned_finished = '{start_date}'
                                WHERE id = {workorder_id}
                                """
                            self.env.cr.execute(query_update)
                    # productivity_ids = productivity_obj.search([('code_id', '=', code_id.id),
                    #                                         ('workorder_id', '=', workorder_id),
                    #                                         ('date_end', '=', False)], limit=1)
                    # if productivity_ids:
                    #     '''Pause'''
                    #     productivity_ids.button_pause()
                    #     self.refresh()
                    productivity_ids = productivity_obj.search([('code_id', '=', code_id.id),
                                                            ('workorder_id', '=', workorder_id)])
                    if productivity_ids:
                        for productivity in productivity_ids:
                            if not productivity.date_end:
                                '''Pause'''
                                productivity.date_end = datetime.now()
                                self.refresh()
                            elif productivity.state == 'in_progress':
                                self.check_parallel(workorder_id)
                                timeline = self.env['mrp.workcenter.productivity']
                                if self.duration < self.duration_expected:
                                    loss_id = self.env['mrp.workcenter.productivity.loss'].search([('loss_type','=','productive')], limit=1)
                                    if not len(loss_id):
                                        raise UserError(_("You need to define at least one productivity loss in the category 'Productivity'. Create one from the Manufacturing app, menu: Configuration / Productivity Losses."))
                                else:
                                    loss_id = self.env['mrp.workcenter.productivity.loss'].search([('loss_type','=','performance')], limit=1)
                                    if not len(loss_id):
                                        raise UserError(_("You need to define at least one productivity loss in the category 'Performance'. Create one from the Manufacturing app, menu: Configuration / Productivity Losses."))
                                if self.production_id.state != 'progress':
                                    self.production_id.write({
                                        'date_start': datetime.now(),
                                    })
                                timeline_id = timeline.create({
                                    'code_id': code_id.id,
                                    'workorder_id': workorder_id,
                                    'workcenter_id': self.workcenter_id.id,
                                    'description': _('Time Tracking: ')+self.env.user.name,
                                    'loss_id': loss_id[0].id,
                                    'state': 'in_progress',
                                    'date_start': datetime.now(),
                                    'user_id': self.env.user.id,  # FIXME sle: can be inconsistent with company_id
                                    'company_id': self.company_id.id,
                                })
                                self.time_progress_ids = timeline_id
                                self.refresh()
                                self.is_user_working = True
                                self.state = 'progress'
                            else:
                                raise UserError(_("you cannot scan a completed piece for this work order."))
                    else:
                        # timeline_id = self.create_timeline(code_id)
                        # check parallel process
                        self.check_parallel(workorder_id)
                        timeline = self.env['mrp.workcenter.productivity']
                        if self.duration < self.duration_expected:
                            loss_id = self.env['mrp.workcenter.productivity.loss'].search([('loss_type','=','productive')], limit=1)
                            if not len(loss_id):
                                raise UserError(_("You need to define at least one productivity loss in the category 'Productivity'. Create one from the Manufacturing app, menu: Configuration / Productivity Losses."))
                        else:
                            loss_id = self.env['mrp.workcenter.productivity.loss'].search([('loss_type','=','performance')], limit=1)
                            if not len(loss_id):
                                raise UserError(_("You need to define at least one productivity loss in the category 'Performance'. Create one from the Manufacturing app, menu: Configuration / Productivity Losses."))
                        if self.production_id.state != 'progress':
                            self.production_id.write({
                                'date_start': datetime.now(),
                            })
                        timeline_id = timeline.create({
                            'code_id': code_id.id,
                            'workorder_id': workorder_id,
                            'workcenter_id': self.workcenter_id.id,
                            'description': _('Time Tracking: ')+self.env.user.name,
                            'loss_id': loss_id[0].id,
                            'state': 'in_progress',
                            'date_start': datetime.now(),
                            'user_id': self.env.user.id,  # FIXME sle: can be inconsistent with company_id
                            'company_id': self.company_id.id,
                        })
                        self.time_progress_ids = timeline_id
                        self.refresh()
                        self.is_user_working = True
                        self.state = 'progress'
                if command == 'end':
                    productivity_ids = productivity_obj.search([('code_id', '=', code_id.id),
                                                            ('workorder_id', '=', workorder_id)
                                                            # ('date_end', '=', False)
                                                            ])
                    minimum_duration = self.env.user.company_id.minimum_duration
                    start_date = productivity_ids[0].date_start
                    end_date = datetime.now()
                    duration = (end_date - start_date).total_seconds()
                    pieces_to_done += 1
                    self.write({'pieces_done': pieces_to_done})
                    if duration < minimum_duration:
                        raise UserError(_("The working duration is too short, please check again"))
                    if productivity_ids:
                        for line in productivity_ids:
                            if not line.date_end:
                                line.write({'date_end': datetime.now(),
                                            'state': 'done'})
                            else:
                                line.write({'state': 'done'})
                        self.refresh()
                        self.is_user_working = True
                    pieces_scanned = []
                    for scanned in self.time_done_ids:
                        if scanned.code_id.id not in pieces_scanned:
                            pieces_scanned.append(scanned.code_id.id)
                    if len(pieces_done) == len(pieces_scanned):
                        wo = self.search([('id', '=', workorder_id)])
                        wo_form = Form(wo)
                        wo = wo_form.save()
                        wo.do_finish()
    
    def do_finish(self):
        # res = super(MrpWorkOrder, self).do_finish()
        workcenter_tab_obj = self.env['workcenter.tab']
        if self.workcenter_id.used_scan_process:
            workcenter_tab_ids = workcenter_tab_obj.search([
                                ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
                                ('parallel_workcenter_id', '=', self.workcenter_id.id)
                                ])
            if workcenter_tab_ids:
                pieces_done = []
                for workcenter in workcenter_tab_ids:
                    pieces_done.append(workcenter.code_id.id)
                pieces_scanned = []
                for scanned in self.time_done_ids:
                    pieces_scanned.append(scanned.code_id.id)
                
                if len(self.time_done_ids) > len(workcenter_tab_ids):
                    for done in self.time_done_ids:
                        if done.code_id.id not in pieces_done:
                            raise UserError(_('You scanned more pieces than needed'))
                for work_tab in workcenter_tab_ids:
                    if work_tab.code_id.id not in pieces_scanned:
                        raise UserError(_('There are missing pieces required for this work order. Please check again'))
                for done in self.time_done_ids:
                    if done.code_id.id not in pieces_done:
                        raise UserError(_('There are pieces that are not assigned to this Work Order . Please check again'))
        return super(MrpWorkOrder, self).do_finish()
        
    def _compute_working_users(self):
        res = super(MrpWorkOrder, self)._compute_working_users()
        for order in self:
            if order.workcenter_id.used_scan_process and order.state != 'done':
                order.is_user_working = True


class MrpWorkCenterProductivity(models.Model):
    '''inherit mrp.workcenter.productivity'''
    _inherit = 'mrp.workcenter.productivity'

    code_id = fields.Many2one('cutting.code', 'Piece to Complete')
    state = fields.Selection([
        ('in_progress', 'In Progress'),
        ('done', 'Done')
        ], string='State', copy=False)
    note = fields.Text('Note')
    
    def button_pause(self):
        view = self.env.ref('lp_mrp.workorder_pause_reason_view')
        wiz = self.env['workorder.pause.reason'].create({
                                            'workorder_id': False,
                                            'wo_productivity_id': self.id})
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'workorder.pause.reason',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': wiz.id,
            'context': self.env.context,
        }
        # self.date_end = datetime.now()
        return True

    def button_done(self):
        self.date_end = datetime.now()
        self.state = 'done'
        return True

class MrpAbstractWorkorder(models.AbstractModel):
    _inherit = "mrp.abstract.workorder"

    @api.onchange('qty_producing')
    def _onchange_qty_producing(self):
        """ Modify the qty currently producing will modify the existing
        workorder line in order to match the new quantity to consume for each
        component and their reserved quantity.
        """
        print("#############",self.qty_producing, self.workcenter_id.used_scan_process)
        if not self.workcenter_id.used_scan_process:
            if self.qty_producing <= 0:
                raise UserError(_('You have to produce at least one %s.') % self.product_uom_id.name)
            line_values = self._update_workorder_lines()
            for values in line_values['to_create']:
                self.env[self._workorder_line_ids()._name].new(values)
            for line in line_values['to_delete']:
                if line in self.raw_workorder_line_ids:
                    self.raw_workorder_line_ids -= line
                else:
                    self.finished_workorder_line_ids -= line
            for line, vals in line_values['to_update'].items():
                line.update(vals)