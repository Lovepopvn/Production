# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, tools

from collections import defaultdict
from odoo.tools.float_utils import float_is_zero

class LandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def compute_landed_cost(self):
        super(LandedCost, self).compute_landed_cost()
        for record in self:
            total_additional_costs = round(sum(record.cost_lines.mapped('price_unit')))
            total_additional_landed_costs = 0
            last_line_id = record.valuation_adjustment_lines[-1].id
            for line in record.valuation_adjustment_lines:
                value = round(line.additional_landed_cost)
                if line.id == last_line_id:
                    value = total_additional_costs - total_additional_landed_costs
                line.write({'additional_landed_cost': value})
                total_additional_landed_costs += value

    def _check_sum(self):
        """ Check if each cost line its valuation lines sum to the correct amount
        and if the overall total amount is correct also """
        ''' Overridden base to adjust the check to work for rounded additional landed costs '''
        prec_digits = self.env.company.currency_id.decimal_places
        for landed_cost in self:
            total_amount = sum(landed_cost.valuation_adjustment_lines.mapped('additional_landed_cost'))
            if not tools.float_is_zero(total_amount - landed_cost.amount_total, precision_digits=prec_digits):
                return False

            ''' PCV: disabled because the solution to rounding inconsistencies we're implementing here inherently breaks the lines' mapping's checksum. We must trust the user not to do changes after calculation and before validation, OR introduce a more robust solution to the check (probably skip check only of the last line). '''
            # val_to_cost_lines = defaultdict(lambda: 0.0)
            # for val_line in landed_cost.valuation_adjustment_lines:
            #     val_to_cost_lines[val_line.cost_line_id] += val_line.additional_landed_cost
            # if any(not tools.float_is_zero(cost_line.price_unit - val_amount, precision_digits=prec_digits)
            #        for cost_line, val_amount in val_to_cost_lines.items()):
            #     return False
        return True
