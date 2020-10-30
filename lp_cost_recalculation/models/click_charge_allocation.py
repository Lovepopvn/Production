# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ClickChargeAllocation(models.Model):
    _name = 'lp_cost_recalculation.click.charge.allocation'
    _description = 'Click Charge Allocation'
    _inherit = 'lp_cost_recalculation.cost.recalculation.abstract'


    account_move_ids = fields.One2many(inverse_name='click_charge_allocation_id')
    delta_line_ids = fields.One2many('lp_cost_recalculation.click.charge.line', 'click_charge_allocation_id', 'Click Charge Lines', copy=False)
    allocation_line_ids = fields.One2many('lp_cost_recalculation.click.charge.consumed.line', 'click_charge_allocation_id', 'Click Charge Consumed Lines', copy=False)


    @api.model
    def get_calculation_type(self):
        return 'click_charge'


    def generate_line(self):
        self.ensure_one_names()
        self._validate_dates()
        self._validate_state()
        manufacturing_orders = self._get_manufacturing_orders()
        calculated_sides = 0
        calculated_cost = 0.0
        for manufacturing_order in manufacturing_orders:
            sides = sum(manufacturing_order.follower_sheets_ids.mapped('total_printed_side'))
            calculated_sides += sides
            cost = sides * manufacturing_order.average_printing_cost_when_done
            calculated_cost += cost
        self.write({'delta_line_ids': [(5, 0, 0)]})
        self.write({'delta_line_ids': [(0, 0, {
            'calculated_sides': calculated_sides,
            'calculated_cost': calculated_cost,
        })]})


    def compute_allocation(self):
        self.ensure_one_names()
        self._validate_dates()
        self._validate_state()
        self._validate_journal_company()

        manufacturing_orders = self._get_manufacturing_orders()
        manufacturing_orders = manufacturing_orders.filtered(lambda r: sum(r.follower_sheets_ids.mapped('total_printed_side')) > 0)
        if not self.delta_line_ids or len(self.delta_line_ids) > 1:
            raise UserError(_("There should be exactly 1 line in List Click Charge to compute allocation."))
        delta_line = self.delta_line_ids[0]
        unit_cost_per_click = delta_line.unit_cost_per_click
        lines = []
        for manufacturing_order in manufacturing_orders:
            line_vals = self._get_allocation_line_vals(manufacturing_order)
            calculated_cost = sum(manufacturing_order.follower_sheets_ids.mapped('total_printed_side')) * unit_cost_per_click
            line_vals.update({
                'calculated_cost': calculated_cost,
                'delta_line_id': delta_line.id,
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

class ClickChargeLine(models.Model):
    _name = 'lp_cost_recalculation.click.charge.line'
    _description = 'Click Charge Line'

    calculated_sides = fields.Integer()
    actual_sides = fields.Integer()
    unit_cost_per_click = fields.Monetary('Actual Average Printing Cost')
    calculated_cost = fields.Monetary()
    actual_cost = fields.Monetary(compute='_compute_delta')
    delta_cost = fields.Monetary(compute='_compute_delta')
    click_charge_allocation_id = fields.Many2one('lp_cost_recalculation.click.charge.allocation', 'Parent Click Charge Allocation')
    currency_id = fields.Many2one('res.currency', string='Currency', related='click_charge_allocation_id.currency_id')


    @api.depends('calculated_cost', 'actual_sides', 'unit_cost_per_click')
    def _compute_delta(self):
        for record in self:
            record.actual_cost = record.actual_sides * record.unit_cost_per_click
            record.delta_cost = record.actual_cost - record.calculated_cost

class ClickChargeConsumedLine(models.Model):
    _name = 'lp_cost_recalculation.click.charge.consumed.line'
    _description = 'Click Charge Consumed Line'
    _inherit = 'lp_cost_recalculation.abstract.allocation.line'

    calculated_cost = fields.Float()
    allocated_value = fields.Float(digits=(32,4))
    click_charge_allocation_id = fields.Many2one('lp_cost_recalculation.click.charge.allocation', 'Parent Click Charge Allocation')
    delta_line_id = fields.Many2one('lp_cost_recalculation.click.charge.line', 'Origin Click Charge Line')
    currency_id = fields.Many2one(related='click_charge_allocation_id.currency_id')
