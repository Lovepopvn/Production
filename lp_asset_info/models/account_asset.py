# -*- coding: utf-8 -*-

from odoo import models, fields, api, _



class AccountAsset(models.Model):
    _inherit = 'account.asset'

    purchased_value = fields.Monetary()
    accumulative_depreciation = fields.Monetary()
    asset_code = fields.Char()