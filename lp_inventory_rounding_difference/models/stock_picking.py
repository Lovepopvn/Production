# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

from math import floor


class StockPicking(models.Model):
    _inherit = "stock.picking"


    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        self._floor_product_cost()
        return res


    def action_done(self):
        res = super(StockPicking, self).action_done()
        self._floor_product_cost()
        return res


    def _floor_product_cost(self):
        counterpart_id = self._get_counterpart_account_id()
        products = self.move_ids_without_package.mapped('product_id')
        for product in products:
            cost = product.standard_price
            cost_floor = floor(cost)
            if cost - cost_floor:
                product._change_standard_price(cost_floor, counterpart_account_id=counterpart_id)


    @api.model
    def _get_counterpart_account_id(self):
        counterpart = self.company_id.inventory_rounding_account_id
        if not counterpart:
            raise ValidationError(_('You must set the Inventory Rounding Account in Accounting Settings.'))
        counterpart_id = counterpart.id
        return counterpart_id


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def process(self):
        res = super(StockImmediateTransfer, self).process()
        self.pick_ids._floor_product_cost()
        return res


class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    def _process(self):
        res = super(StockBackorderConfirmation, self)._process()
        self.pick_ids._floor_product_cost()
        return res
