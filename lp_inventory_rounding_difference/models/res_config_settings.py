# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    inventory_rounding_account_id = fields.Many2one('account.account', 'Inventory Rounding Account', related='company_id.inventory_rounding_account_id', readonly=False)
