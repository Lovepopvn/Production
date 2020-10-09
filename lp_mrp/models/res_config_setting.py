# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    minimum_duration = fields.Integer(
        related='company_id.minimum_duration',
        readonly=False)
    pricelist_id = fields.Many2one(related='company_id.pricelist_id',
        readonly=False)