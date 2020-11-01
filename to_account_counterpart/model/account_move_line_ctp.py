from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import ValidationError, UserError


class AccountMoveLineCTP(models.Model):
    _name = 'account.move.line.ctp'
    _inherit = 'mail.thread'
    _description = "Journal Item Counterpart"

    @api.model
    def _get_dr_aml_domain(self):
        return [('countered_status', '!=', 'fully'), ('credit', '=', 0.0)]

    @api.model
    def _get_cr_aml_domain(self):
        return [('countered_status', '!=', 'fully'), ('debit', '=', 0.0)]

    company_currency_id = fields.Many2one('res.currency', string='Company Currency', compute='_compute_company_currency', store=True)
    dr_aml_id = fields.Many2one('account.move.line', string='Debit Move Line', required=True, ondelete='cascade',
                                track_visibility='onchange', domain=_get_dr_aml_domain)
    dr_account_id = fields.Many2one(related='dr_aml_id.account_id', readonly=True, store=True)
    dr_aml_debit = fields.Monetary(related='dr_aml_id.debit', currency_field='company_currency_id', readonly=True, store=True,
                                   help="The debit value of the debit journal item")
    cr_aml_id = fields.Many2one('account.move.line', string='Credit Move Line', required=True, ondelete='cascade',
                                track_visibility='onchange', domain=_get_cr_aml_domain)
    cr_account_id = fields.Many2one(related='cr_aml_id.account_id', readonly=True, store=True)
    cr_aml_credit = fields.Monetary(related='cr_aml_id.credit', currency_field='company_currency_id', readonly=True, store=True,
                                    help="The credit value of the credit journal item")

    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency', store=True)

    countered_amt = fields.Monetary(string='Countered Amount', currency_field='company_currency_id', track_visibility='onchange',
                                   help="The amount in company's currency that matches the two lines in a counterpart operation.")

    countered_amt_currency = fields.Monetary(string='Countered Amount Currency', currency_field='currency_id', track_visibility='onchange',
                                   help="The amount in the original currency that matches the two lines in a counterpart operation.")

    move_id = fields.Many2one('account.move', string='Journal Entry', compute='_compute_move_id', store=True)

    @api.constrains('company_currency_id', 'countered_amt', 'dr_aml_id', 'cr_aml_id')
    def _check_max_countered_amt(self):
        for r in self:
            abs_min_cr_dr = min([abs(r.dr_aml_id.balance), abs(r.cr_aml_id.balance)])
            abs_countered_amt = abs(r.countered_amt)
            if float_compare(abs_countered_amt, abs_min_cr_dr, precision_rounding=r.company_currency_id.rounding) == 1:
                raise ValidationError(_("Countered Amount must not be bigger than the debit and credit amounts. Debugging information:\n"
                                        "Countered Amount: %s\n"
                                        "Debit Line: %s, Debit: %s\n"
                                        "Credit Line: %s, Credit: %s\n")
                                        % (r.countered_amt, r.dr_aml_id.display_name, r.dr_aml_id.debit, r.cr_aml_id.display_name, r.cr_aml_id.credit))

    @api.onchange('dr_aml_id', 'cr_aml_id')
    def _onchange_amls(self):
        res = {}
        if self.dr_aml_id and self.dr_aml_id.move_id:
            res['domain'] = {'cr_aml_id':self._get_cr_aml_domain() + [('id', 'in', self.dr_aml_id.move_id.line_ids.ids)]}
        elif self.cr_aml_id and self.cr_aml_id.move_id:
            res['domain'] = {'dr_aml_id':self._get_dr_aml_domain() + [('id', 'in', self.cr_aml_id.move_id.line_ids.ids)]}
        else:
            res['domain'] = {}

    @api.constrains('countered_amt', 'dr_aml_id', 'cr_aml_id')
    def _check_countered_amt(self):
        for r in self:
            max_countered_amt = min([r.dr_aml_id.debit, r.cr_aml_id.credit])
            if float_compare(r.countered_amt, max_countered_amt, precision_digits=r.company_currency_id.decimal_places) == 1:
                raise ValidationError(_("Countered Amount for the Journal Item '%s' and the Journal Item '%s' must not be greater than %s")
                                      % (r.dr_aml_id.display_name, r.cr_aml_id.display_name, max_countered_amt))

    @api.depends('dr_aml_id.company_currency_id', 'cr_aml_id.company_currency_id')
    def _compute_company_currency(self):
        for r in self:
            r.company_currency_id = r.dr_aml_id.company_currency_id or r.cr_aml_id.company_currency_id or self.env.user.company_id.currency_id

    @api.depends('dr_aml_id.currency_id', 'cr_aml_id.currency_id')
    def _compute_currency(self):
        for r in self:
            r.currency_id = r.dr_aml_id.currency_id or r.cr_aml_id.currency_id or False

    @api.constrains('dr_aml_id')
    def _check_dr_aml_id(self):
        for r in self:
            if float_is_zero(r.dr_aml_id.debit, precision_digits=r.company_currency_id.decimal_places):
                raise ValidationError(_("The debit move line in the Journal Item Counterpart has zero debit"))

    @api.constrains('cr_aml_id')
    def _check_cr_aml_id(self):
        for r in self:
            if float_is_zero(r.cr_aml_id.credit, precision_digits=r.company_currency_id.decimal_places):
                raise ValidationError(_("The credit move line in the Journal Item Counterpart has zero credit"))

    @api.depends('dr_aml_id', 'dr_aml_id.move_id', 'cr_aml_id', 'cr_aml_id.move_id')
    def _compute_move_id(self):
        for r in self:
            r.move_id = r.dr_aml_id.move_id or r.cr_aml_id.move_id

    @api.constrains('dr_aml_id', 'cr_aml_id')
    def _check_dr_cd_lines(self):
        for r in self:
            if not r.dr_aml_id.move_id or not r.cr_aml_id.move_id:
                raise ValidationError(_("Both the journal items of the same counterpart must have the journal entry defined"))
            if r.dr_aml_id.move_id.id != r.cr_aml_id.move_id.id:
                raise UserError(_("Both the journal items of the same counterpart must be in the same account journal entry"))

    def unlink(self):
        if not self.env.context.get('force_unlink', False) and not self.env.user.has_group('base.group_system'):
            for r in self:
                if r.dr_aml_id:
                    if r.dr_aml_id.move_id.state == 'posted':
                        raise UserError(_("You cannot delete counterparts of a posted journal entry (%s). Please cancel the entry"
                                          " to get the counterparts deleted.") % (r.dr_aml_id.move_id.name,))
                if r.cr_aml_id:
                    if r.cr_aml_id.move_id.state == 'posted':
                        raise UserError(_("You cannot delete counterparts of a posted journal entry (%s). Please cancel the entry"
                                          " to get the counterparts deleted.") % (r.cr_aml_id.move_id.name,))
        return super(AccountMoveLineCTP, self).unlink()

    def _get_display_name(self):
        self.ensure_one()
        if self.move_id and self.dr_aml_id and self.cr_aml_id:
            return '%s <-> %s: %s [%s]' % (self.dr_account_id.code, self.cr_account_id.code, self.countered_amt or 0.0, self.move_id.name)
        else:
            return self._name

    def name_get(self):
        result = []
        for r in self:
            result.append((r.id, r._get_display_name()))
        return result

