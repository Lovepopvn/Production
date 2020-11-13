from odoo import models, api, fields, _
from odoo.exceptions import UserError


class WizardAccountCounterpartGenerator(models.TransientModel):
    _name = 'wizard.account.counterpart.generator'
    _description = 'Account Counterpart Generating Wizard'

    type = fields.Selection([
        ('missing_only', 'Missing Only'),
        ('regeneration', 'Regeneration')
        ], string='Generation Type', default='missing_only', required=True)

    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')

    journal_ids = fields.Many2many('account.journal', string='Journals',
                                   help="Select one or more journals, or leave empty to generate counterparts for the whole accounting data available")
    recreate_for_the_partially = fields.Boolean(string='Recreate for Partially Countered Entries', default=False)
    rec_limit = fields.Integer(string='Limit Number of Journal Entries', default=250, help="This is to limit the number of journal"
                               " entries to process to avoid CPU timeout")
    ignore_if_lines_count_larger_than = fields.Integer(string='Ignore if more than', default=0, help="If a positive is set, the Journal Entries "
                                                       "having a number of Journal Items larger then this will be ignored. Set zero (0) to disable "
                                                       "this feature")

    
    def _get_ingored_move_ids(self):
        self.ensure_one()
        ids = []
        if self.ignore_if_lines_count_larger_than:
            self.env.cr.execute("""
            SELECT m.id
            FROM account_move AS m
            GROUP BY m.id
            HAVING (select count(*) from account_move_line where move_id = m.id) > 100    
            """)
            row = self.env.cr.fetchone()
            while row:
                ids.append(row[0])
                row = self.env.cr.fetchone()
        return ids

    @api.onchange('type')
    def _onchange_type(self):
        if self.type == 'missing_only':
            self.recreate_for_the_partially = True
        else:
            self.recreate_for_the_partially = False

    @api.constrains('from_date', 'to_date')
    def _check_dates(self):
        for r in self:
            if r.from_date and r.to_date and r.from_date > r.to_date:
                raise UserError(_("The 'From Date' must not be later than the 'To Date'"))

    
    def action_generate_counterparts(self):
        self.ensure_one()
        AccountMove = self.env['account.move']
        AccountMoveLineCtp = self.env['account.move.line.ctp']

        date_domain = []
        if self.from_date:
            date_domain += [('date', '>=', self.from_date)]
        if self.to_date:
            date_domain += [('date', '<=', self.to_date)]

        date_domain += [('state', '=', 'posted')]

        domain = date_domain + [('line_ids', '!=', False)]
        ctp_to_unlink = AccountMoveLineCtp
        if self.type == 'missing_only':
            domain.append(('countered_status', '!=', 'fully'))
            if self.recreate_for_the_partially:
                partially_countered_move_ids = AccountMove.search([('countered_status', '=', 'partially')] + date_domain)
                ctp_to_unlink |= partially_countered_move_ids.mapped('line_ids.ctp_ids')
        else:
            ctp_to_unlink |= AccountMoveLineCtp.search([])

        if ctp_to_unlink:
            ctp_to_unlink.with_context(force_unlink=True).unlink()
            self.env.cr.commit()

        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        ignore_ids = self._get_ingored_move_ids()
        if ignore_ids:
            domain += [('id', 'not in', ignore_ids)]

        if self.rec_limit > 0:
            move_ids = AccountMove.search(domain + [('line_ids', '!=', False)], limit=self.rec_limit)
        else:
            move_ids = AccountMove.search(domain + [('line_ids', '!=', False)])
        return move_ids.action_smart_create_counterpart()

    
    def cron_create_counterparts(self, rec_limit=250, ignore_if_lines_count_larger_than=0):
        generator_id = self.create({
            'type': 'missing_only',
            'recreate_for_the_partially': True,
            'rec_limit': rec_limit,
            'ignore_if_lines_count_larger_than': ignore_if_lines_count_larger_than
            })
        generator_id.action_generate_counterparts()
        return True

