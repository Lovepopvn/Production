from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    cr_ctp_ids = fields.One2many('account.move.line.ctp', 'dr_aml_id', string='Credit Counterparts',
                                 help="Technical field to link credit counterparts with this journal item")
    dr_ctp_ids = fields.One2many('account.move.line.ctp', 'cr_aml_id', string='Debit Counterparts',
                                 help="Technical field to link debit counterparts with this journal item")

    ctp_ids = fields.Many2many('account.move.line.ctp', string='Counterparts', compute='_compute_ctp_ids')
    ctp_aml_ids = fields.Many2many('account.move.line', 'aml_counterpart_rel', 'aml1_id', 'aml2_id',
                                   string='Countered Journal Items', compute='_compute_ctp_aml_ids', store=True,
                                   help="The Journal Items that are countered with this Journal Item")
    ctp_account_ids = fields.Many2many('account.account', 'account_ctp_account_rel', 'aml_id', 'account_id',
                                       string='Countered Accounts', compute='_compute_ctp_account_ids', store=True,
                                       help="The Accounts that are countered with the account of this Journal Item")

    countered_amt = fields.Monetary(string='Countered Amount', currency_field='company_currency_id',
                                      compute='_compute_countered_amt', store=True, help="The amount that has been"
                                      " countered for this journal item")

    countered_amt_currency = fields.Monetary(string='Countered Amount Currency', currency_field='currency_id',
                                             compute='_compute_countered_amt_currency', store=True, help="The amount in the original currency"
                                             " that has been countered for this journal item")

    countered_status = fields.Selection([
        ('none', 'Not Countered'),
        ('partially', 'Partially Countered'),
        ('fully', 'Fully Countered'),
        ], default='none', index=True, compute='_compute_countered_status', store=True, string='Countered Status', help="A technical"
        " field to indicate that this journal item has either countered fully or partially or not-yet-countered")

    def is_debit(self):
        self.ensure_one()
        return float_is_zero(self.credit, precision_digits=self.company_currency_id.decimal_places)

    def is_credit(self):
        self.ensure_one()
        return float_is_zero(self.debit, precision_digits=self.company_currency_id.decimal_places)

    def is_zero(self):
        self.ensure_one()
        return float_is_zero(self.credit, precision_digits=self.company_currency_id.decimal_places) and float_is_zero(self.debit, precision_digits=self.company_currency_id.decimal_places)

    @api.constrains('cr_ctp_ids', 'dr_ctp_ids')
    def _check_ctp(self):
        for r in self:
            if r.cr_ctp_ids and r.dr_ctp_ids:
                raise ValidationError(_("An Journal Item must not have both both credit and debit counterparts. It should have either only."))

    @api.depends('dr_ctp_ids', 'cr_ctp_ids')
    def _compute_ctp_ids(self):
        for r in self:
            r.ctp_ids = r.dr_ctp_ids + r.cr_ctp_ids

    @api.depends('cr_ctp_ids', 'cr_ctp_ids.cr_aml_id', 'dr_ctp_ids', 'dr_ctp_ids.dr_aml_id')
    def _compute_ctp_aml_ids(self):
        for r in self:
            r.ctp_aml_ids = r.cr_ctp_ids.mapped('cr_aml_id') + r.dr_ctp_ids.mapped('dr_aml_id')

    @api.depends('ctp_aml_ids', 'ctp_aml_ids.account_id')
    def _compute_ctp_account_ids(self):
        for r in self:
            r.ctp_account_ids = r.ctp_aml_ids.mapped('account_id')

    @api.depends('cr_ctp_ids', 'cr_ctp_ids.countered_amt', 'dr_ctp_ids', 'dr_ctp_ids.countered_amt', 'balance')
    def _compute_countered_amt(self):
        for r in self:
            if float_compare(r.balance, 0.0, precision_digits=r.company_currency_id.decimal_places) == 1:
                r.countered_amt = sum(r.cr_ctp_ids.mapped('countered_amt'))
            elif float_compare(r.balance, 0.0, precision_digits=r.company_currency_id.decimal_places) == -1:
                r.countered_amt = sum(r.dr_ctp_ids.mapped('countered_amt'))
            else:
                r.countered_amt = 0.0

    @api.depends('cr_ctp_ids', 'cr_ctp_ids.countered_amt_currency', 'dr_ctp_ids', 'dr_ctp_ids.countered_amt_currency', 'amount_currency')
    def _compute_countered_amt_currency(self):
        for r in self:
            if float_compare(r.amount_currency, 0.0, precision_digits=r.currency_id.decimal_places) == 1:
                r.countered_amt_currency = sum(r.cr_ctp_ids.mapped('countered_amt_currency'))
            elif float_compare(r.amount_currency, 0.0, precision_digits=r.currency_id.decimal_places) == -1:
                r.countered_amt_currency = sum(r.dr_ctp_ids.mapped('countered_amt_currency'))
            else:
                r.countered_amt_currency = 0.0

    @api.depends('debit', 'credit', 'countered_amt')
    def _compute_countered_status(self):
        for r in self:
            prec = r.company_currency_id.decimal_places
            countered_amt_is_zero = float_is_zero(r.countered_amt, precision_digits=prec)

            if r.is_zero():
                    r.countered_status = 'fully'
            elif r.is_debit():
                if float_compare(r.countered_amt, r.debit, precision_digits=prec) >= 0:
                    r.countered_status = 'fully'
                elif countered_amt_is_zero:
                    r.countered_status = 'none'
                else:
                    r.countered_status = 'partially'
            else:
                if float_compare(r.countered_amt, r.credit, precision_digits=prec) >= 0:
                    r.countered_status = 'fully'
                elif countered_amt_is_zero:
                    r.countered_status = 'none'
                else:
                    r.countered_status = 'partially'

    def _prepare_counterpart_data(self, ctp_aml_id, countered_amt=None, countered_amt_currency=None):
        self.ensure_one()

        if countered_amt_currency == None:
            countered_amt_currency = min([abs(self.amount_currency), abs(ctp_aml_id.amount_currency)])

        data = {}

        if self.is_zero() and ctp_aml_id.is_zero():
            data.update({
                'dr_aml_id': self.id,
                'cr_aml_id':ctp_aml_id.id,
                'countered_amt': 0.0,
                'countered_amt_currency': 0.0,
                })
        # self is a debit line and ctp_aml is a credit line
        elif self.is_debit() and ctp_aml_id.is_credit():
            if countered_amt == None:
                countered_amt = min([self.debit, ctp_aml_id.credit])

            data.update({
                'dr_aml_id': self.id,
                'cr_aml_id':ctp_aml_id.id,
                'countered_amt': countered_amt,
                'countered_amt_currency': countered_amt_currency,
                })
        # self is a credit line and ctp_aml is a debit line
        elif self.is_credit() and ctp_aml_id.is_debit():
            if countered_amt == None:
                countered_amt = min([self.credit, ctp_aml_id.debit])

            data.update({
                'dr_aml_id': ctp_aml_id.id,
                'cr_aml_id':self.id,
                'countered_amt': countered_amt,
                'countered_amt_currency': countered_amt_currency,
                })
        else:
            raise ValidationError(_("The journal item '%s' could not be countered with the journal item %s")
                                  % (self.display_name, ctp_aml_id.display_name))

        return data

    def create_aml_counterpart(self, ctp_aml_id, countered_amt=None, countered_amt_currency=None):
        self.ensure_one()
        return self.env['account.move.line.ctp'].create(self._prepare_counterpart_data(ctp_aml_id, countered_amt, countered_amt_currency))

    def _get_max_countered_amt(self, aml_ids):
        self.ensure_one()
        aml_ids_sum = sum(abs(aml_id.balance) for aml_id in aml_ids)
        if float_compare(aml_ids_sum, abs(self.balance), precision_rounding=self.company_currency_id.rounding) >= 0:
            max_countered_amt = abs(self.balance)
        else:
            max_countered_amt = aml_ids_sum

        return aml_ids_sum, max_countered_amt

    def _get_max_countered_amt_currency(self, aml_ids):
        self.ensure_one()
        rounding = self.currency_id.rounding if self.currency_id else 0.01
        aml_ids_currency_sum = sum(abs(aml_id.amount_currency) for aml_id in aml_ids)
        if float_compare(aml_ids_currency_sum, abs(self.amount_currency), precision_rounding=rounding) >= 0:
            max_countered_amt_currency = abs(self.amount_currency)
        else:
            max_countered_amt_currency = aml_ids_currency_sum
        return aml_ids_currency_sum, max_countered_amt_currency

    def create_aml_counterparts(self, aml_ids):
        self.ensure_one()
        if self.countered_status == 'fully':
            return True

        if self.is_zero():
            return True
        else:
            if self.is_credit():
                aml_ids = aml_ids.filtered(lambda l: l.is_debit() and not l.is_zero() and l.countered_status != 'fully')
            else:
                aml_ids = aml_ids.filtered(lambda l: l.is_credit() and not l.is_zero() and l.countered_status != 'fully')

            aml_ids_sum, max_countered_amt = self._get_max_countered_amt(aml_ids)
            aml_ids_currency_sum, max_countered_amt_currency = self._get_max_countered_amt_currency(aml_ids)

            len_aml_ids = len(aml_ids)
            for aml_id in aml_ids:
                _logger.debug("There are %s counterparts to be created for the line '%s' of the journal entry '%s'",
                              len_aml_ids, aml_id.display_name, self.move_id.name)
                len_aml_ids -= 1

                countered_amt = max_countered_amt * abs(aml_id.balance) / aml_ids_sum
                rounding = aml_id.currency_id.rounding if aml_id.currency_id else 0.01
                if not float_is_zero(aml_ids_currency_sum, precision_rounding=rounding):
                    countered_amt_currency = max_countered_amt_currency * abs(aml_id.amount_currency) / aml_ids_currency_sum
                else:
                    countered_amt_currency = None
                self.create_aml_counterpart(aml_id, countered_amt, countered_amt_currency)
                _logger.debug("Counterpart has been created for the Journal Item '%s' of the Journal Entry '%s'.", self.display_name, self.move_id.name)

        return True

    def _get_display_name(self):
        self.ensure_one()
        name = self.move_id.name
        if self.ref:
            name += '(' + self.ref + ')'

        if self.is_zero():
            name += _(" [Zero Value]")
        elif self.is_credit():
            name += ' [%s %s]' % (_("Credit"), self.account_id.code)
        else:
            name += ' [%s %s]' % (_("Debit"), self.account_id.code)

        return name

    
    def name_get(self):
        result = []
        for r in self:
            result.append((r.id, r._get_display_name()))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('move_id.name', '=ilike', '%' + name + '%'), ('ref', '=ilike', '%' + name + '%'), ('name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()

    
    @api.depends('ctp_account_ids')
    def _get_counterpart(self):
        for r in self:
            r.counterpart = ",".join(r.ctp_account_ids.mapped('code'))

