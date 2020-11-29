# -*- coding: utf-8 -*-
'''Mrp Work Order'''
from odoo import fields, models, api, _
from odoo.exceptions import UserError, Warning
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
                        created = False
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
                                if not created:
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
                                    created = True
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
                    pieces_to_done += 1
                    self.write({'pieces_done': pieces_to_done})
                    if productivity_ids:
                        check = False
                        for line in productivity_ids:
                            if not line.date_end:
                                check = True
                                start_date = line.date_start
                                end_date = datetime.now()
                                duration = (end_date - start_date).total_seconds()
                                if duration < minimum_duration:
                                    raise UserError(_("The working duration is too short, please check again"))
                                line.write({'date_end': datetime.now(),
                                            'state': 'done'})
                            else:
                                line.write({'state': 'done'})
                        if not check:
                            raise UserError(_("You cannot end piece that is being paused, please try again"))
                        self.refresh()
                        self.is_user_working = True
                    pieces_scanned = []
                    for scanned in self.time_done_ids:
                        if scanned.code_id.id not in pieces_scanned:
                            pieces_scanned.append(scanned.code_id.id)
                    if len(pieces_done) == len(pieces_scanned):
                        query = f"""SELECT id FROM mrp_workcenter_productivity
                                WHERE code_id != {code_id.id} AND
                                workorder_id = {workorder_id} AND
                                state = 'in_progress'
                        """ 
                        productivity_ids = self._cr.execute(query)
                        productivity_ids = self._cr.fetchall()
                        # check if there is other pieces still on In Progress, if not set done Workorder
                        if not productivity_ids:
                            wo = self.search([('id', '=', workorder_id)])
                            wo_form = Form(wo)
                            wo = wo_form.save()
                            wo.do_finish()
    
    def do_finish(self):
        # res = super(MrpWorkOrder, self).do_finish()
        workcenter_tab_obj = self.env['workcenter.tab']
        # set warning when there is issue in scanning pieces
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
        if self.workcenter_id.ending_work_center:
            # search if there is other workorder not done yet.
            # if find it it will be warning when mark as done last workorder
            wo_ids = self.search([
                ('production_id', '=', self.production_id.id), 
                ('state', 'not in', ('done','cancel')),
                ('id', '!=', self.id)])
            if len(wo_ids) > 0:
                raise UserError(_('Before mark as done last workorder, please mark as done others workorder first'))
        res = super(MrpWorkOrder, self).do_finish()
        # set done component which consumed in the work order
        self.production_id.post_inventory()
        if self.production_id.workorder_ids:
            all_wo_done = True
            for wo in self.production_id.workorder_ids:
                if wo.state != 'done':
                    all_wo_done = False
            if all_wo_done == True:
                # finds all manufacturing orders that contain this manufacturing as a source
                mos = self.env['mrp.production'].search([('origin','ilike',self.production_id.name)])
                # loops through the manufacturing orders
                for mo in mos:
                    # checks to see the state
                    if mo.state != 'done' and mo.state != 'cancel':
                        warn = """
                                Before completing this manufacturing order (%s),\n  all manufacturing orders that produce sub-assemblies must first be complete.\n
                                %s (which produces %s x [%s] %s) is not yet complete.\n
                                Truoc khi bam thao tac hoan thanh don hang tong (%s),\n ban phai hoan thanh truoc cac don hang nho cua don hang tong nay.\n
                                Don hang %s (gom %s don hang x [%s] %s la chua duoc hoan thanh.)
                                """ % (self.production_id.name,mo.name,str(int(mo.product_qty)),mo.product_id.default_code,mo.product_id.name,
                                        self.production_id.name,mo.name,str(int(mo.product_qty)),mo.product_id.default_code,mo.product_id.name)
                        raise Warning(warn)
                self.production_id.button_mark_done()
                self.production_id.write({'state': 'done'})
        return res
    
    def write(self, values):
        res = super(MrpWorkOrder, self).write(values)
        for wo in self:
            if values.get('time_ids') and wo.production_id.state in ('done','cancel'):
                raise UserError(_('You can not edit time tracking if Manufacturing order is done'))
        return res

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
            'name': _('Pieces Pause Reason'),
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