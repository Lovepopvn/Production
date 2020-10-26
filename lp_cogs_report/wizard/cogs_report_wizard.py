# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.tools.misc import formatLang, format_date as odoo_format_date, get_lang
from odoo.exceptions import ValidationError
from odoo.addons.http_routing.models.ir_http import slugify
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter

import base64
import io

from io import StringIO, BytesIO
from datetime import datetime
from dateutil.relativedelta import relativedelta

DATE_FORMAT = _('%d/%m/%Y')
EXCELDATE_FORMAT = _('dd/mm/yyyy')
FNDATE_FORMAT = _('%y%m%d')

HEADERS = [_('Budgetary Position'), _('G/L Accounts'), _('Analytic Account'), _('Start Date of Budget Line'), _('End Date of Budget Line'), _('Planned Amount'), _('Practical Amount in period'), _('Achievement in period'), ]

# months in (int, str) tuples
MONTHS = [(str(month), '%02d' % month) for month in list(range(1, 13))]

TIMEZONE_RELATIVEDELTA = relativedelta(hours=7)

DEFAULT_YEAR = lambda l: str((datetime.now()+TIMEZONE_RELATIVEDELTA).year)
DEFAULT_MONTH = lambda l: str((datetime.now()+TIMEZONE_RELATIVEDELTA).month)

STATES = [('draft', 'Draft'), ('allocation_derived', 'Allocation Derived'), ('posted', 'Posted')]
DEFAULT_STATE = STATES[0][0]

class WizardCOGSPackReport(models.TransientModel):
    _name = 'wizard.cogs.pack.report'
    _description = 'Wizard COGS Pack Report'

    @api.model
    def _get_available_years(initial_year=2020):
        now = datetime.now() + TIMEZONE_RELATIVEDELTA
        current_year = now.year
        available_years_int = list(range(initial_year, current_year + 1))
        available_years = [(str(year), str(year)) for year in available_years_int]
        return available_years

    year = fields.Selection(_get_available_years(), default=DEFAULT_YEAR)
    month = fields.Selection(MONTHS, default=DEFAULT_MONTH)
    date_from = fields.Datetime(compute='_compute_date_range', store=True)
    date_to = fields.Datetime(compute='_compute_date_range', store=True)
    material_loss_id = fields.Many2one(
        'lp_cost_recalculation.material.loss.allocation', 'Material Loss Allocation')
    labor_cost_id = fields.Many2one(
        'lp_cost_recalculation.labor.cost.allocation', 'Labor Cost Allocation')
    click_charge_id = fields.Many2one(
        'lp_cost_recalculation.click.charge.allocation', 'Click Charge Allocation')
    overhead_cost_id = fields.Many2one(
        'lp_cost_recalculation.overhead.cost.allocation', 'Overhead Cost Allocation')

    # budget_id = fields.Many2one('crossovered.budget', string='Budget',required=True)
    # start_date = fields.Date(string='Start Date',required=True)
    # end_date = fields.Date(string='End Date',required=True)
    name = fields.Char(string="Filename", readonly=True)
    data_file = fields.Binary(string="File", readonly=True)


    @api.onchange('budget_id')
    def _onchange_budget_id(self):
        if self.budget_id:
            self.start_date = self.budget_id.date_from
            self.end_date = self.budget_id.date_to
        else:
            self.start_date = self.end_date = False

    def _prepare_report_data(self):
        self.ensure_one()
        self.check_dates()
        AccountMoveLine = self.env['account.move.line']
        AccountAnalyticLine = self.env['account.analytic.line']

        budget = self.budget_id

        report_data = {
            'sheet_name': budget.name,
            'report_name': _('Budget "%s" (%s - %s)') % (budget.name, budget.date_from.strftime(DATE_FORMAT), budget.date_to.strftime(DATE_FORMAT)),
            'report_company': _("Entity: %s") % (budget.company_id.name or '',),
            'report_period': _("Report period: %s - %s") % (self.start_date.strftime(DATE_FORMAT), self.end_date.strftime(DATE_FORMAT)),
            'budget_lines': [],
        }
        for line in budget.crossovered_budget_line:
            budget_line = {
                'date_from': line.date_from,
                'date_to': line.date_to,
                'planned_amount': line.planned_amount,
            }
            aml_domain = [
                ('date', '>=', line.date_from),
                ('date', '<=', line.date_to),
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date),
            ]
            aal_domain = list(aml_domain)
            if line.general_budget_id and line.general_budget_id.account_ids:
                budget_line['budgetary_position'] = line.general_budget_id.name
                aml_domain.extend([
                    ('account_id', 'in', line.general_budget_id.account_ids.ids),
                    ('move_id.state', '=', 'posted'),
                ])
                aal_domain.append(('general_account_id', 'in', line.general_budget_id.account_ids.ids))
            if line.analytic_account_id:
                budget_line['analytic_account'] = line.analytic_account_id.name
                aml_domain.append(('analytic_account_id', '=', line.analytic_account_id.id))
                aal_domain.append(('account_id', '=', line.analytic_account_id.id))
                aals = AccountAnalyticLine.search(aal_domain)
                practical_amount_period = sum(aals.mapped('amount'))
            else:
                amls = AccountMoveLine.search(aml_domain)
                practical_amount_period = sum(amls.mapped(lambda l: l.credit - l.debit))
            achievement = 0.0
            if line.planned_amount:
                achievement = practical_amount_period / line.planned_amount
            budget_line['practical_amount'] = practical_amount_period
            budget_line['achievement'] = achievement
            if line.general_budget_id:
                account_lines = []
                for account in line.general_budget_id.account_ids:
                    # Write account line
                    if line.analytic_account_id:
                        account_practical_amount_period = sum(
                            aals.filtered(lambda l: l.general_account_id.id == account.id)\
                            .mapped('amount')
                        )
                    else:
                        account_practical_amount_period = sum(
                            amls.filtered(lambda l: l.account_id.id == account.id)\
                            .mapped(lambda l: l.credit - l.debit)
                        )
                    achievement = 0.0
                    if line.planned_amount:
                        achievement = account_practical_amount_period / line.planned_amount
                    account_lines.append({
                        # 'name': (account.code or '') + ' ' + (account.en_name or account.name or ''),
                        'name': (account.code or '') + ' ' + (account.en_name or 'False'),
                        'practical_amount': account_practical_amount_period,
                        'achievement': achievement,
                    })
                budget_line['account_lines'] = account_lines
            report_data['budget_lines'].append(budget_line)
        return report_data


    def button_generate_excel(self):
        self.ensure_one()
        self.check_dates()
        budget = self.budget_id
        report_data = self._prepare_report_data()
        currency = budget.company_id.currency_id

        currency_number = '#,##0'
        if currency.decimal_places:
            currency_number += ('.' + '0' * currency.decimal_places)
        if currency.position == 'after':
            currency_format = currency_number + ' "' + currency.symbol + '"'
        else:
            currency_format = '"' + currency.symbol + '" ' + currency_number

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Formats
        # Report Information
        report_text = workbook.add_format({
            'bold': True,
        })

        # Table header
        table_header = workbook.add_format({
            'border': 1,
            'text_wrap': True,
            'valign': 'vcenter',
            'align': 'center',
            'bold': True,
            'bg_color': '#dddddd',
        })

        # Budget line
        budget_line_format = {
            'border': 1,
            'text_wrap': True,
            'valign':'vcenter',
            'bold': True,
            'bg_color': '#eeeeee',
        }
        budget_line = workbook.add_format(budget_line_format)

        budget_line_currency_format = dict(budget_line_format)
        budget_line_currency_format['num_format'] = currency_format
        budget_line_currency = workbook.add_format(budget_line_currency_format)

        budget_line_percentage_format = dict(budget_line_format)
        budget_line_percentage_format['num_format'] = '0.00%'
        budget_line_percentage = workbook.add_format(budget_line_percentage_format)

        budget_lineDATE_FORMAT = dict(budget_line_format)
        budget_lineDATE_FORMAT['num_format'] = EXCELDATE_FORMAT
        budget_line_date = workbook.add_format(budget_lineDATE_FORMAT)

        # Account breakdown line
        account_line = workbook.add_format({
            'border': 1,
            'align': 'left'
        })
        account_line_currency = workbook.add_format({
            'border': 1,
            'align': 'right',
            'num_format': currency_format,
        })
        account_line_percentage = workbook.add_format({
            'border': 1,
            'align': 'right',
            'num_format': '0.00%',
        })

        sheet = workbook.add_worksheet(report_data['sheet_name'])

        # Set column width
        sheet.set_column(0, 1, 30)
        sheet.set_column(2, len(HEADERS) - 1, 27)
        headers_offset_y = 4
        headers_offset_x = 0

        # Write report information
        sheet.merge_range('A1:B1', report_data['report_name'], report_text)
        sheet.merge_range("A2:B2", report_data['report_company'], report_text)
        sheet.merge_range("A3:B3", report_data['report_period'], report_text)

        # Write table headers
        for header_index in range(len(HEADERS)):
            sheet.write(headers_offset_y, header_index, HEADERS[header_index], table_header)

        lines_offset_y = headers_offset_y + 1
        for budget_line_data in report_data['budget_lines']:
            # Write budget line with totals
            line_offset_y = lines_offset_y
            lines_offset_y += 1
            for lines_offset_x in range(len(HEADERS)):
                sheet.write_blank(line_offset_y, lines_offset_x, None, budget_line)
            if 'budgetary_position' in budget_line_data:
                sheet.write(line_offset_y, 0, budget_line_data['budgetary_position'], budget_line)
            if 'analytic_account' in budget_line_data:
                sheet.write(line_offset_y, 2, budget_line_data['analytic_account'], budget_line)
            sheet.write(line_offset_y, 3, budget_line_data['date_from'], budget_line_date)
            sheet.write(line_offset_y, 4, budget_line_data['date_to'], budget_line_date)
            sheet.write(line_offset_y, 5, budget_line_data['planned_amount'], budget_line_currency)
            sheet.write(line_offset_y, 6, budget_line_data['practical_amount'], budget_line_currency)
            sheet.write(line_offset_y, 7, budget_line_data['achievement'], budget_line_percentage)
            if 'account_lines' in budget_line_data:
                for line in budget_line_data['account_lines']:
                    # Write account line
                    for lines_offset_x in range(len(HEADERS)):
                        sheet.write_blank(lines_offset_y, lines_offset_x, None, account_line)
                    sheet.write(lines_offset_y, 1, line['name'], account_line)
                    sheet.write(lines_offset_y, 6, line['practical_amount'], account_line_currency)
                    sheet.write(lines_offset_y, 7, line['achievement'], account_line_percentage)
                    lines_offset_y += 1

        workbook.close()
        out = base64.encodebytes(output.getvalue())
        output.close()
        filename = _('budget_report_%s-%s_%s') % (self.start_date.strftime(FNDATE_FORMAT), self.end_date.strftime(FNDATE_FORMAT), self.budget_id.name)
        filename = slugify(filename) + '.xlsx'
        return self.set_data_excel(out, filename)


    def set_data_excel(self, out, filename):
        """ Update data_file and name based from previous process output. And return action url for download excel. """
        self.write({
            'data_file': out,
            'name': filename
        })

        return {
            'type': 'ir.actions.act_url',
            'name': filename,
            'url': '/web/content/%s/%s/data_file/%s' % (self._name, self.id, filename),
        }

    def check_dates(self):
        for report in self:
            budget = report.budget_id
            if not (budget.date_from <= report.start_date <= report.end_date <= budget.date_to):
                raise ValidationError(_("The selected report dates (%s - %s) are outside the budget's period (%s - %s).") % (report.start_date.strftime(DATE_FORMAT), report.end_date.strftime(DATE_FORMAT), budget.date_from.strftime(DATE_FORMAT), budget.date_to.strftime(DATE_FORMAT)))
