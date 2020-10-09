# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    material_loss_allocation_id = fields.Many2one('lp_cost_recalculation.material.loss.allocation', 'Origin Material Loss Allocation')
    labor_cost_allocation_id = fields.Many2one('lp_cost_recalculation.labor.cost.allocation', 'Origin Labor Cost Allocation')
    click_charge_allocation_id = fields.Many2one('lp_cost_recalculation.click.charge.allocation', 'Origin Click Charge Allocation')
    overhead_cost_allocation_id = fields.Many2one('lp_cost_recalculation.overhead.cost.allocation', 'Origin Overhead Cost Allocation')
