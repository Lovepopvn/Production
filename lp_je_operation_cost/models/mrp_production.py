# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def button_plan(self):
        # Make sure JEs can be created when MO is done
        self.production_location_id.validate_valuation_accounts()
        return super(MrpProduction, self).button_plan()
