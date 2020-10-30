# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
import logging

_logger = logging.getLogger(__name__)

class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    def button_validate(self):
        for cost in self:
            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                print("LANDED COST",line.product_id.standard_price)
                line.product_id.prev_standard_price = line.product_id.standard_price * line.product_id.qty_available
        return super(StockLandedCost, self).button_validate()
