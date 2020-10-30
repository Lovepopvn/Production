from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class AccountTax(models.Model):
    _inherit = 'account.tax'

    non_tax_type = fields.Selection([('non_taxable','Non Taxable'), ('tax_exempt','Tax Exempt')], string="Non Tax Type")

    @api.constrains('amount','non_tax_type')
    def constrains_non_tax_amount(self):
        for rec in self:
            if rec.amount != 0.0 and rec.non_tax_type:
                non_tax_type = dict(rec._fields['non_tax_type'].selection).get(rec.non_tax_type)
                raise UserError(_('Non tax type is %s then amount should be 0!') % (non_tax_type,))