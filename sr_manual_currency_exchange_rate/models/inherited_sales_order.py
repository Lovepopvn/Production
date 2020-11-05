# -*- coding: utf-8 -*-
##############################################################################
#
#    This module uses OpenERP, Open Source Management Solution Framework.
#    Copyright (C) 2017-Today Sitaram
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from odoo import models, fields, api


class SalesOrder(models.Model):
    _inherit = 'sale.order'

    apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Currency Exchange')
    company_currency_id = fields.Many2one('res.currency', 'Company Currency', related='company_id.currency_id')
    manual_currency_exchange_rate_inverted = fields.Float(string='Inverted Manual Currency Exchange Rate', help='Input the amount in the company currency that is equal to 1 in the selected currency', digits=(12, 9))
    manual_currency_exchange_rate = fields.Float(string='Manual Currency Exchange Rate', compute='_compute_exchange_rate', digits=(12, 12))
    active_manual_currency_rate = fields.Boolean('active Manual Currency', default=False)


    @api.depends('manual_currency_exchange_rate_inverted')
    def _compute_exchange_rate(self):
        for rec in self:
            if rec.manual_currency_exchange_rate_inverted:
                rec.manual_currency_exchange_rate = 1/rec.manual_currency_exchange_rate_inverted
            else:
                rec.manual_currency_exchange_rate = 0


    def _prepare_invoice(self):
        result = super(SalesOrder, self)._prepare_invoice()
        result.update({
            'apply_manual_currency_exchange':self.apply_manual_currency_exchange,
            'manual_currency_exchange_rate':self.manual_currency_exchange_rate,
            })
        return result

    @api.onchange('company_currency_id','currency_id')
    def onchange_currency_id(self):
        if self.company_currency_id or self.currency_id:
            if self.company_currency_id != self.currency_id:
                self.active_manual_currency_rate = True
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        if self.order_id.active_manual_currency_rate:
            self = self.with_context(
                    manual_rate=self.order_id.manual_currency_exchange_rate,
                    active_manutal_currency = self.order_id.apply_manual_currency_exchange,
                )
        if not self.product_uom or not self.product_id:
            self.price_unit = 0.0
            return
        if self.order_id.pricelist_id and self.order_id.partner_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            self.price_unit = self.env['account.tax'].with_context(manual_currency_rate=self.order_id.manual_currency_exchange_rate)._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)

