# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class OverheadCostAllocation(models.Model):
    _name = 'lp_cost_recalculation.overhead.cost.allocation'
    _description = 'Model for allocating overhead cost allocation retrospectively'
    _inherit = 'lp_cost_recalculation.cost.recalculation.abstract'


    account_move_ids = fields.One2many(inverse_name='overhead_cost_allocation_id')
    delta_line_ids = fields.One2many('lp_cost_recalculation.overhead.cost.line', 'overhead_cost_allocation_id', 'Overhead Cost Lines', copy=False)
    allocation_line_ids = fields.One2many('lp_cost_recalculation.overhead.cost.consumed.line', 'overhead_cost_allocation_id', 'Overhead Cost Consumed Lines', copy=False)


    @api.model
    def get_calculation_type(self):
        return 'overhead_cost'


    def compute_allocation(self):
        self.ensure_one_names()
        self._validate_dates()
        self._validate_state()
        self._validate_journal_company()
        manufacturing_orders = self._get_manufacturing_orders()
        self._validate_product_ceq_factor(manufacturing_orders)
        lines = []
        for manufacturing_order in manufacturing_orders:
            line_vals = self._get_allocation_line_vals(manufacturing_order, process_ceq=True)
            lines.append((0, 0, line_vals))
        self.write({'allocation_line_ids': lines})

        self._process_allocation_lines()
        self.write({'state': 'allocation_derived'})


    def validate(self):
        self.ensure_one_names()
        self._create_journal_entries()
        counterpart_account = self.company_id.make_to_stock_allocation_counterpart_account_overhead_cost_id
        wip_counterpart_account = self.company_id.wip_pack_allocation_counterpart_account_overhead_cost_id
        self._update_costs(counterpart_account.id, wip_counterpart_account.id)
        self.write({'state': 'posted'})


    def export_allocation_lines(self):
        return self._export_allocation_lines()

class OverheadCostLine(models.Model):
    _name = 'lp_cost_recalculation.overhead.cost.line'
    _description = 'List Input Overhead Cost: lines for computing overhead cost allocation'

    overhead_cost_account_id = fields.Many2one('account.account', 'Overhead Cost Account')
    actual_cost = fields.Monetary()
    overhead_cost_allocation_id = fields.Many2one('lp_cost_recalculation.overhead.cost.allocation', 'Parent Overhead Cost Allocation')
    currency_id = fields.Many2one('res.currency', string='Currency', related='overhead_cost_allocation_id.currency_id')

class OverheadCostConsumedLine(models.Model):
    _name = 'lp_cost_recalculation.overhead.cost.consumed.line'
    _description = 'List LP Consumed Overhead Cost: lines for computing consumed overhead cost allocation'
    _inherit = 'lp_cost_recalculation.abstract.allocation.line'

    ceq_factor = fields.Float('CEQ Factor')
    ceq_converted_qty = fields.Float('CEQ Converted Quantity')
    overhead_cost_allocation = fields.Float(digits=(32,4))
    overhead_cost_allocation_id = fields.Many2one('lp_cost_recalculation.overhead.cost.allocation', 'Parent Overhead Cost Allocation')
    currency_id = fields.Many2one(related='overhead_cost_allocation_id.currency_id')
