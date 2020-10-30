# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _


class AccountAccount(models.Model):
    _inherit = "account.account"

    fixing_rounding = fields.Boolean("Apply Fixing Rounding")
