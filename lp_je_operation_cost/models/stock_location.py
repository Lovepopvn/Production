# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class StockLocation(models.Model):
    _inherit = 'stock.location'

    operation_valuation_out_account_id = fields.Many2one('account.account', 'Stock Valuation Account (Outgoing, Operation)')
    printing_valuation_out_account_id = fields.Many2one('account.account', 'Stock Valuation Account (Outgoing, Printing)')

    def validate_valuation_accounts(self):
        errors = []
        for location in self:
            if not location.printing_valuation_out_account_id:
                errors.append(('Stock Valuation Account (Outgoing, Printing)', location.name_get()[0][1]))
            if not location.operation_valuation_out_account_id:
                errors.append(('Stock Valuation Account (Outgoing, Operation)', location.name_get()[0][1]))
        if errors:
            message = _('Following Stock Valuation Accounts must be set:') + '\n'
            for account in errors:
                message += ('\n' + _('"%s" on the "%s" location') % account)
            raise ValidationError(message)
