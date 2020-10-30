# -*- coding: utf-8 -*-

from odoo import fields, models, _, api


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    @api.model
    def _update_products_by_items(self, currency, items, products, template=True):
        if template:
            product_field = 'product_tmpl_id'
        else:
            product_field = 'product_id'
        for product in products:
            items_product = items.filtered(lambda i: i[product_field].id == product.id)
            item = items_product.sorted(lambda i: i.id, reverse=True)[0]
            product.write({
                'transfer_price': item.fixed_price,
                'transfer_price_currency_id': currency.id,
            })

    @api.model
    def update_products_transfer_price(self):
        today = fields.Date.today()

        for pricelist in self:
            currency = pricelist.currency_id
            items_with_products = pricelist.item_ids.filtered(lambda i: \
                i.applied_on in ('0_product_variant', '1_product')
            )
            items_valid = items_with_products.filtered(lambda i: \
                (not i.date_start or i.date_start <= today) and \
                (not i.date_end or i.date_end >= today) and \
                i.min_quantity == 0 and i.compute_price == 'fixed' \
            )
            items_product = items_valid.filtered(lambda i: i.applied_on == '1_product')
            products = items_product.mapped('product_tmpl_id')
            items_variant = items_valid.filtered(lambda i: i.applied_on == '0_product_variant')
            variants = items_variant.mapped('product_id')
            self._update_products_by_items(currency, items_product, products)
            self._update_products_by_items(currency, items_variant, variants, False)

            data_zero = {
                'transfer_price': 0.0,
                'transfer_price_currency_id': currency.id,
            }

            all_products = items_with_products\
                .filtered(lambda i: i.applied_on == '1_product').mapped('product_tmpl_id')
            expired_products = all_products.filtered(lambda p: p.id not in products.ids)
            expired_products.write(data_zero)

            all_variants = items_with_products\
                .filtered(lambda i: i.applied_on == '0_product_variant').mapped('product_id')
            expired_variants = all_variants.filtered(lambda v: v.id not in variants.ids)
            expired_variants.write(data_zero)


    @api.model
    def transfer_price_update(self, company_id=False):
        if not company_id:
            company = self.env.company
        else:
            company = self.env.company.browse(company_id)
        pricelist = company.transfer_price_update_pricelist_id
        pricelist.update_products_transfer_price()
