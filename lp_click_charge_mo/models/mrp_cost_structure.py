# -*- coding: utf-8 -*-

from odoo import api, models


class MrpCostStructure(models.AbstractModel):
    _inherit = 'report.mrp_account_enterprise.mrp_cost_structure'

    def get_lines(self, productions):
        res = super(MrpCostStructure, self).get_lines(productions)
        for resource in res:
            res_mos = productions.filtered(lambda p: p.product_id.id == resource['product'].id)
            costs_sides = {}
            for mo in res_mos:
                mo_sides = sum(mo.follower_sheets_ids.mapped('total_printed_side'))
                mo_cost = mo_sides * mo.average_printing_cost_when_done
                costs_sides[mo_cost] = mo_sides
            total_cost = sum(costs_sides.keys())
            total_printed_sides = sum(costs_sides.values())
            click_rate = 0
            if total_printed_sides != 0:
                click_rate = total_cost / total_printed_sides
            resource['printing_cost'] = [total_printed_sides, click_rate, total_cost]
        return res
