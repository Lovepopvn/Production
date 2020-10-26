# -*- coding: utf-8 -*-
'''Res Company'''
from odoo import fields, models, _


class ResCompany(models.Model):
    '''Inherit Res.Company'''
    _inherit = 'res.company'

    factory_constants_id = fields.Many2one('factory.constants', 'Factory Constants')
    minimum_duration = fields.Integer()
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Pricelist for shipping item.")
