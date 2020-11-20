# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class LaborCostAllocation(models.Model):
    _name = 'lp_cost_recalculation.labor.cost.allocation'
    _description = 'Labor Cost Allocation'
    _inherit = 'lp_cost_recalculation.cost.recalculation.abstract'


    account_move_ids = fields.One2many(inverse_name='labor_cost_allocation_id')
    delta_line_ids = fields.One2many('lp_cost_recalculation.labor.cost.gap.line', 'labor_cost_allocation_id', 'Labor Cost Lines', copy=False)
    allocation_line_ids = fields.One2many('lp_cost_recalculation.labor.cost.consumed.line', 'labor_cost_allocation_id', 'Labor Cost Consumed Lines', copy=False)
    total_calculated_labor_cost = fields.Monetary(compute='_compute_cost_sums')
    total_calculated_labor_cost_by_accounting = fields.Monetary(readonly=True)
    total_calculated_labor_cost_corrected = fields.Monetary(compute='_compute_cost_sums')
    error_to_correct = fields.Monetary(compute='_compute_cost_sums')


    @api.depends('delta_line_ids.calculated_labor_cost', 'delta_line_ids.wrong_input_correction')
    def _compute_cost_sums(self):
        for record in self:
            record.total_calculated_labor_cost = \
                sum(record.delta_line_ids.mapped('calculated_labor_cost'))
            record.total_calculated_labor_cost_corrected = \
                sum(record.delta_line_ids.mapped('corrected_calculated_cost'))
            record.error_to_correct = \
                record.total_calculated_labor_cost_by_accounting - record.total_calculated_labor_cost_corrected


    def button_draft(self):
        self._validate_state(1)
        self.write({
            'delta_line_ids': [(5, 0, 0)],
            'allocation_line_ids': [(5, 0, 0)],
            'state': 'draft',
            'allocation_lines_xlsx': False,
            'total_calculated_labor_cost_by_accounting': False,
        })


    @api.model
    def get_calculation_type(self):
        return 'labor_cost'


    def summarize_calculated_labor_cost(self):
        self.ensure_one_names()
        self._validate_dates()
        self._validate_state()
        manufacturing_orders = self._get_manufacturing_orders().filtered(lambda l: not l.mo_for_samples)
        workcenters = {}
        # based on mrp_account_enterprise/reports/mrp_cost_structure.py:21
        Workorders = self.env['mrp.workorder'].search([('production_id', 'in', manufacturing_orders.ids)])
        if not Workorders:
            raise UserError(_("Didn't find any Work Orders in the selected period."))
        else:
            # Done through SQL because that's how base Odoo does it; simplified the original query because we need less information
            query_str = """
                SELECT w.operation_id, sum(t.duration) / 60 * wc.costs_hour "total_cost"
                FROM mrp_workcenter_productivity t
                LEFT JOIN mrp_workorder w ON (w.id = t.workorder_id)
                LEFT JOIN mrp_workcenter wc ON (wc.id = t.workcenter_id )
                WHERE t.workorder_id IS NOT NULL AND t.workorder_id IN %s
                GROUP BY w.operation_id, wc.costs_hour
            """
            self.env.cr.execute(query_str, (tuple(Workorders.ids), ))
            RoutingWorkcenter = self.env['mrp.routing.workcenter']
            for production_id, total_cost in self.env.cr.fetchall():
                workcenter = RoutingWorkcenter.browse([production_id]).workcenter_id
                if workcenter.id in workcenters:
                    workcenters[workcenter.id] += total_cost
                else:
                    workcenters[workcenter.id] = total_cost
                # operations.append([user, op_id, op_name, duration / 60.0, cost_hour])
        lines = []
        for workcenter_id in workcenters:
            lines.append((0, 0, {'workcenter_id': workcenter_id, 'calculated_labor_cost': workcenters[workcenter_id]}))
        if not lines:
            raise UserError(_("No labor costs found for Work Orders in the selected period."))
        self.write({'delta_line_ids': [(5, 0, 0)]})
        self.write({'delta_line_ids': lines})
        self._calculate_total_calculated_labor_cost_by_accounting()


    def _calculate_total_calculated_labor_cost_by_accounting(self):
        AML = self.env['account.move.line']
        for record in self:
            account_id = record._get_accounts()['make_to_stock_counterpart']
            domain = [
                ('account_id', '=', account_id),
                ('date', '>=', record.date_from),
                ('date', '<=', record.date_to),
            ]
            total_cost = sum(AML.search(domain).mapped('credit'))
            record.write({'total_calculated_labor_cost_by_accounting': total_cost})


    def compute_allocation(self):
        self.ensure_one_names()
        self._validate_dates()
        self._validate_state()
        self._validate_journal_company()

        if self.error_to_correct:
            raise ValidationError(_("You need to input Wrong Input Correction first to make Error To Correct 0."))

        manufacturing_orders = self._get_manufacturing_orders().filtered(lambda l: not l.mo_for_samples)
        for manufacturing_order in manufacturing_orders:
            lines = []
            for loss_line in self.delta_line_ids:
                Workorders = self.env['mrp.workorder'].search([
                    # ('production_id', 'in', manufacturing_orders.ids),
                    ('production_id', '=', manufacturing_order.id),
                    ('workcenter_id', '=', loss_line.workcenter_id.id),
                    ('state', '=', 'done')
                ])
                if not Workorders:
                    continue
                line_vals = self._get_allocation_line_vals(manufacturing_order)

                calculated_cost = 0.0
                # get data for calculated_cost
                query_str = """
                    SELECT sum(t.duration) / 60 * wc.costs_hour "total_cost"
                    FROM mrp_workcenter_productivity t
                    LEFT JOIN mrp_workorder w ON (w.id = t.workorder_id)
                    LEFT JOIN mrp_workcenter wc ON (wc.id = t.workcenter_id )
                    WHERE t.workorder_id IS NOT NULL AND t.workorder_id IN %s
                    GROUP BY wc.id
                """
                self.env.cr.execute(query_str, (tuple(Workorders.ids), ))
                RoutingWorkcenter = self.env['mrp.routing.workcenter']
                for total_cost in self.env.cr.fetchall()[0]:
                    calculated_cost += total_cost

                # line preparation
                line_vals.update({
                    'workcenter_id': loss_line.workcenter_id.id,
                    'calculated_cost': calculated_cost,
                    'delta_line_id': loss_line.id,
                })
                lines.append((0, 0, line_vals))
            self.write({'allocation_line_ids': lines})

        self._process_allocation_lines()
        self.write({'state': 'allocation_derived'})


    def validate(self):
        self.ensure_one_names()
        self._create_journal_entries()
        self._update_costs()
        self.write({'state': 'posted'})


    def export_allocation_lines(self):
        return self._export_allocation_lines()

class LaborCostGapLine(models.Model):
    _name = 'lp_cost_recalculation.labor.cost.gap.line'
    _description = 'Labor Cost Gap Line'

    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center')
    calculated_labor_cost = fields.Monetary()
    wrong_input_correction = fields.Monetary(help='For cases where users changed working time after marking MO as done')
    corrected_calculated_cost = fields.Monetary(compute='_compute_delta', store=True)
    actual_labor_cost = fields.Monetary()
    delta_cost = fields.Monetary(compute='_compute_delta', store=True)
    labor_cost_allocation_id = fields.Many2one('lp_cost_recalculation.labor.cost.allocation', 'Parent Labor Cost Allocation')
    currency_id = fields.Many2one('res.currency', string='Currency', related='labor_cost_allocation_id.currency_id')


    @api.depends('actual_labor_cost', 'calculated_labor_cost', 'wrong_input_correction')
    def _compute_delta(self):
        for record in self:
            record.corrected_calculated_cost = \
                record.calculated_labor_cost + record.wrong_input_correction
            record.delta_cost = record.actual_labor_cost - record.corrected_calculated_cost

class LaborCostConsumedLine(models.Model):
    _name = 'lp_cost_recalculation.labor.cost.consumed.line'
    _description = 'Labor Cost Consumed Line'
    _inherit = 'lp_cost_recalculation.abstract.allocation.line'

    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center')
    calculated_cost = fields.Monetary()
    gap_allocated_value = fields.Float(digits=(32,4))
    labor_cost_allocation_id = fields.Many2one('lp_cost_recalculation.labor.cost.allocation', 'Parent Labor Cost Allocation')
    delta_line_id = fields.Many2one('lp_cost_recalculation.labor.cost.gap.line', 'Origin Labor Cost Gap Line')
    currency_id = fields.Many2one(related='labor_cost_allocation_id.currency_id')
