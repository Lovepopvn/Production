# -*- coding: utf-8 -*-

from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    def product_price_update_before_done(self, forced_qty=None):
        # adapt standard price on incomming moves if the product cost_method is 'average'
        for move in self.filtered(lambda move: move._is_in() and move.with_context(force_company=move.company_id.id).product_id.cost_method == 'average'):
            move.product_id.prev_standard_price = move.product_id.standard_price * move.product_id.qty_available
        return super(StockMove, self).product_price_update_before_done(forced_qty)
