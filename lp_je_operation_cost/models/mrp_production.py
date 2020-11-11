# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def button_plan(self):
        # Make sure JEs can be created when MO is done
        self.production_location_id.validate_valuation_accounts()
        return super(MrpProduction, self).button_plan()
    
    def _cal_price(self, consumed_moves):
        """
            Replace function in mrp_accunt to update inventory valuation based on finish good value
            Set a price unit on the finished move according to `consumed_moves`.
        """
        work_center_cost = 0
        finished_move = self.move_finished_ids.filtered(lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel') and x.quantity_done > 0)
        if finished_move:
            finished_move.ensure_one()
            for work_order in self.workorder_ids:
                time_lines = work_order.time_ids.filtered(lambda x: x.date_end and not x.cost_already_recorded)
                duration = sum(time_lines.mapped('duration'))
                time_lines.write({'cost_already_recorded': True})
                work_center_cost += (duration / 60.0) * work_order.workcenter_id.costs_hour
            if finished_move.product_id.cost_method in ('fifo', 'average'):
                qty_done = finished_move.product_uom._compute_quantity(finished_move.quantity_done, finished_move.product_id.uom_id)
                extra_cost = self.extra_cost * qty_done
                if all(move.state in ('done', 'cancel') for move in self.move_raw_ids):
                    comp_moves_done = self.move_raw_ids
                    consumed_moves |= comp_moves_done
                # add printing cost
                click_rate = 0
                factory_constants = self.env.company.factory_constants_id
                if factory_constants:
                    click_rate = factory_constants.average_printing_cost
                total_printed_sides = sum(self.follower_sheets_ids.mapped('total_printed_side'))
                printing_cost = round(total_printed_sides * click_rate)
                valuation_value = -sum(consumed_moves.sudo().stock_valuation_layer_ids.mapped('value'))
                finished_move.price_unit = (valuation_value + work_center_cost + extra_cost + printing_cost) / qty_done
        return True
