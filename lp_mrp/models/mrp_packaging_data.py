# -*- coding: utf-8 -*-
'''Packaging Data BoM'''
from odoo import fields, models, _


class MrpPackagingData(models.Model):
    '''new model mrp.packaging.data'''
    _name = 'mrp.packaging.data'
    _description = 'Bom packaging Data'

    bom_id = fields.Many2one('mrp.bom', 'Bill of Material')
    product_id = fields.Many2one('product.product', 'Product') 
    quantity = fields.Integer('Quantity per product', default=1)
    unit_package = fields.Integer('Units per package')

    def name_get(self):
        result = []
        for pack in self:
            if pack.product_id:
                result.append((pack.id, _("[PACK] %s")%(pack.product_id.name)))
            else:
                result.append((pack.id, _("[PACK] %s")%(pack.id)))
        return result