from odoo import models, fields, api, _


class AccountGeneralLedger(models.AbstractModel):
    _inherit = 'account.general.ledger'

    @api.model
    def _get_custom_lines(self, options, line_id=None):
        offset = int(options.get('lines_offset', 0))
        lines = []
        context = self.env.context
        company_id = self.env.user.company_id
        used_currency = company_id.currency_id
        dt_from = options['date'].get('date_from')
        line_id = line_id and int(line_id.split('_')[1]) or None
        aml_lines = []
        # Aml go back to the beginning of the user chosen range but the amount on the account line should go back to either the beginning of the fy or the beginning of times depending on the account
        grouped_accounts = self.with_context(date_from_aml=dt_from, date_from=dt_from and company_id.compute_fiscalyear_dates(fields.Date.from_string(dt_from))['date_from'] or None)._group_by_account_id(options, line_id)
        sorted_accounts = sorted(grouped_accounts, key=lambda a: a.code)
        unfold_all = context.get('print_mode') and len(options.get('unfolded_lines')) == 0
        sum_debit = sum_credit = sum_balance = 0
        sum_initial_balance = 0
        for account in sorted_accounts:
            display_name = account.code + " " + account.name
            if options.get('filter_accounts'):
                # skip all accounts where both the code and the name don't start with the given filtering string
                if not any(
                        [display_name_part.lower().startswith(options['filter_accounts'].lower()) for display_name_part
                         in display_name.split(' ')]):
                    continue
            debit = grouped_accounts[account]['debit']
            credit = grouped_accounts[account]['credit']
            balance = grouped_accounts[account]['balance']
            sum_initial_balance += grouped_accounts[account]['initial_bal']['balance']
            sum_debit += debit
            sum_credit += credit
            sum_balance += balance

        return {
            'initial_balance':sum_initial_balance,
            'debit': sum_debit,
            'credit': sum_credit,
            'balance': sum_balance,
        }
