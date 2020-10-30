# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    inventory_rounding_account_id = fields.Many2one('account.account', 'Inventory Rounding Account')

