from odoo import api, models, fields
from odoo.tools import float_compare

import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    countered_status = fields.Selection([
        ('none', 'Not Countered'),
        ('partially', 'Partially Countered'),
        ('fully', 'Fully Countered'),
        ], default='none', index=True, compute='_compute_countered_status', store=True, string='Countered Status', help="A technical"
        " field to indicate that this journal entry has either countered fully or partially or not-yet-countered")

    ctp_ids = fields.Many2many('account.move.line.ctp', string='Counterparts Mapping', compute='_compute_ctp_ids', store=False)

    @api.depends('line_ids', 'line_ids.ctp_ids')
    def _compute_ctp_ids(self):
        for r in self:
            r.ctp_ids = r.mapped('line_ids.ctp_ids')

    @api.depends('line_ids', 'line_ids.countered_status')
    def _compute_countered_status(self):
        for r in self:
            if not r.line_ids:
                r.countered_status = 'none'
                continue

            if all(line.countered_status == 'fully' for line in r.line_ids):
                r.countered_status = 'fully'
            elif all(line.countered_status == 'none' for line in r.line_ids):
                r.countered_status = 'none'
            else:
                r.countered_status = 'partially'

    
    def action_delete_counterpart(self):
        self.mapped('line_ids.ctp_ids').with_context(force_unlink=self.env.context.get('force_unlink_ctp', False)).unlink()
        zero_line_ids = self.env['account.move.line'].search([
                ('move_id', 'in', self.ids),
                ('debit', '=', 0.0),
                ('credit', '=', 0.0),
                ('countered_status', '=', 'fully')
            ])
        if zero_line_ids:
            zero_line_ids.write({'countered_status':'none'})

    
    def action_smart_create_counterpart(self):
        AccMoveLine = self.env['account.move.line']

        # delete the counterparts of the partially countered moves in self
        partially_countered_move_ids = self.filtered(lambda m: m.countered_status == 'partially')
        if partially_countered_move_ids:
            partially_countered_move_ids.action_delete_counterpart()

        for r in self:
            # PROCESS NONE ZERO LINES
            dr_line_ids = AccMoveLine.search([
                ('move_id', '=', r.id),
                ('debit', '!=', 0.0),
                ('countered_status', '!=', 'fully')
            ])
            len_dr_line_ids = len(dr_line_ids)

            cr_line_ids = AccMoveLine.search([
                ('move_id', '=', r.id),
                ('credit', '!=', 0.0),
                ('countered_status', '!=', 'fully')
            ])
            len_cr_line_ids = len(cr_line_ids)

            _logger.debug("The Journal Entry '%s' has %s credit lines and %s debit lines to be processed for counterparts",
                          r.name, len_dr_line_ids, len_cr_line_ids)

            # one debit line and one or more credit lines
            if len_dr_line_ids == 1:
                dr_line_ids[0].create_aml_counterparts(cr_line_ids)

            # one credit line and one or more debit lines
            elif len_cr_line_ids == 1:
                cr_line_ids[0].create_aml_counterparts(dr_line_ids)

            # multiple debit lines and multiple credit lines, experimental
            elif self.env.context.get('process_m2m_counterpart', True):

                # FIRST, process lines that matching debit <-> credit amount having same partner property's value.
                # I.e. Both counterpart having the same partner or no partner at all
                for dr_line_id in dr_line_ids:
                    _logger.debug("There are %s debit lines of the journal entry '%s' to process for the case of debit <-> credit amount matching",
                                  len_dr_line_ids, r.name)
                    len_dr_line_ids -= 1

                    dr_line_prec = dr_line_id.company_currency_id.decimal_places

                    # try to match the next credit line which has same amount
                    if cr_line_ids and (cr_line_ids[0].id == dr_line_id.id - 1 or cr_line_ids[0].id == dr_line_id.id + 1) and float_compare(dr_line_id.debit, cr_line_ids[0].credit, precision_digits=dr_line_prec) == 0:
                        match = cr_line_ids[0]

                    # try to match lines with same partner for the first
                    elif dr_line_id.partner_id:
                        match = cr_line_ids.filtered(lambda l: l.partner_id.id == dr_line_id.partner_id.id \
                                                     and float_compare(dr_line_id.debit, l.credit, precision_digits=dr_line_prec) == 0)
                    # or lines with no partner at all for the second
                    else:
                        match = cr_line_ids.filtered(lambda l: not l.partner_id \
                                                     and float_compare(dr_line_id.debit, l.credit, precision_digits=dr_line_prec) == 0)

                    if match:
                        dr_line_id.create_aml_counterparts(match[0])
                        dr_line_ids -= dr_line_id
                        cr_line_ids -= match[0]
                        continue

                # SECOND, process lines having same partner property's value. I.e. Both counterpart having the same partner or no partner at all
                dr_line_ids = dr_line_ids.filtered(lambda l: l.countered_status != 'fully')
                cr_line_ids = cr_line_ids.filtered(lambda l: l.countered_status != 'fully')
                len_dr_line_ids = len(dr_line_ids)
                for dr_line_id in dr_line_ids:
                    _logger.debug("There are %s debit lines of the journal entry '%s' to process for the case of debit <-> credit amount non-matching",
                                  len_dr_line_ids, r.name)
                    len_dr_line_ids -= 1

                    if dr_line_id.partner_id:
                        match_cr_line_ids = cr_line_ids.filtered(lambda l: l.partner_id.id == dr_line_id.partner_id.id and l.countered_status != 'fully')
                    else:
                        match_cr_line_ids = cr_line_ids.filtered(lambda l: not l.partner_id and l.countered_status != 'fully')

                    if match_cr_line_ids:
                        dr_line_id.create_aml_counterparts(match_cr_line_ids)

                # THIRD, process the remaining lines no matter partners are
                for dr_line_id in dr_line_ids.filtered(lambda l: l.countered_status != 'fully'):
                    match_cr_line_ids = cr_line_ids.filtered(lambda l: l.countered_status != 'fully')
                    if match_cr_line_ids:
                        dr_line_id.create_aml_counterparts(match_cr_line_ids)

            # PROCESS ZERO LINES
            zero_line_ids = AccMoveLine.search([
                ('move_id', '=', r.id),
                ('debit', '=', 0.0),
                ('credit', '=', 0.0),
                ('countered_status', '!=', 'fully')
            ])
            if zero_line_ids:
                zero_line_ids._compute_countered_status()

        return True

    
    def button_cancel(self):
        res = super(AccountMove, self).button_cancel()
        self.with_context(force_unlink_ctp=True).action_delete_counterpart()
        return res

    
    def post(self):
        self.action_smart_create_counterpart()
        return super(AccountMove, self).post()

