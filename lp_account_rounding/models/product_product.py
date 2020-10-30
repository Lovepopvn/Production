# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    prev_standard_price = fields.Float('Previous Amount Valuation', related='product_tmpl_id.prev_standard_price', digits='Product Price', readonly=False)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    prev_standard_price = fields.Float("Previous Amount Valuation", digits='Product Price')
