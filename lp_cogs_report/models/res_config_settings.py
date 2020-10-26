# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    cogs_report_category_raw_id = fields.Many2one(
        'product.category', 'COGS Report Product Category for Raw Material')
    cogs_report_category_sub_id = fields.Many2one(
        'product.category', 'COGS Report Product Category for Sub Material')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cogs_report_category_raw_id = fields.Many2one(
        'product.category', 'COGS Report Product Category for Raw Material',
        related='company_id.cogs_report_category_raw_id', readonly=False)
    cogs_report_category_sub_id = fields.Many2one(
        'product.category', 'COGS Report Product Category for Sub Material',
        related='company_id.cogs_report_category_sub_id', readonly=False)
