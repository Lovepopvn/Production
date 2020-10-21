# -*- coding: utf-8 -*-

from odoo import models, fields, api

class FactoryConstants(models.Model):
    _inherit = 'factory.constants'

    currency_id = fields.Many2one('res.currency', 'Currency')
    average_printing_cost = fields.Monetary()
