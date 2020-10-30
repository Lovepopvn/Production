# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import base64
import io
import time

import xlwt
from dateutil.relativedelta import relativedelta
from odoo import fields, models, _
from odoo.exceptions import UserError


class BiAccountAgedPartnerBalance(models.TransientModel):
    _name = 'bi.account.aged.partner.balance'

    period_length = fields.Integer(string='Period Length (days)', required=True, default=30)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True)
    date_from = fields.Date(default=lambda *a: time.strftime('%Y-%m-%d'))
    result_selection = fields.Selection([
        ('customer', 'Receivable Accounts'),
        ('supplier', 'Payable Accounts'),
        ('customer_supplier', 'Receivable and Payable Accounts')
    ], string="Partner's", required=True, default='customer')
    target_move = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all', 'All Entries'),
    ], string='Target Moves', required=True, default='posted')


    def excel_header(self,worksheet,res):
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'dd/mm/yyyy'
        style_header = xlwt.easyxf(
            "font:height 300; font: name Liberation Sans, bold on,color black; align: horiz center")
        style_table_header = xlwt.easyxf(
            "font: name Liberation Sans, bold on,color black; align: horiz center")

        worksheet.row(0).height_mismatch = True
        worksheet.row(0).height = 500
        worksheet.write_merge(0, 0, 0, 5, "Aged Partner Balance", style=style_header)
        worksheet.write(2, 0, 'Start Date')
        worksheet.write(2, 1, 'Period Length (days)')
        worksheet.write(2, 2, "Partner's")
        worksheet.write(2, 3, "Target Moves")
        worksheet.write(3, 0, self.date_from or '-', date_format)
        worksheet.write(3, 1, self.period_length)
        worksheet.write(3, 2, self.result_selection)
        worksheet.write(3, 3, 'All Posted Entries' if self.target_move == 'posted' else 'All Entries')
        worksheet.write(5, 0, 'Partners', style=style_table_header)
        worksheet.write(5, 1, 'Not due', style=style_table_header)
        worksheet.write(5, 2, res['4']['name'], style=style_table_header)
        worksheet.write(5, 3, res['3']['name'], style=style_table_header)
        worksheet.write(5, 4, res['2']['name'], style=style_table_header)
        worksheet.write(5, 5, res['1']['name'], style=style_table_header)
        worksheet.write(5, 6, res['0']['name'], style=style_table_header)
        worksheet.write(5, 7, "Total")

    def print_report_aged_partner(self):
        if self.period_length <= 0:
            raise UserError(_('You must set a period length greater than 0.'))
        if not self.date_from:
            raise UserError(_('You must set a start date.'))

        start = self.date_from
        data = {}
        res = {}
        used_context = {}
        for i in range(5)[::-1]:
            stop = start - relativedelta(days=self.period_length - 1)
            res[str(i)] = {
                'name': (i != 0 and (
                            str((5 - (i + 1)) * self.period_length) + '-' + str((5 - i) * self.period_length)) or (
                                     '+' + str(4 * self.period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)
        data['form'] = ({
            'target_move': self.target_move,
            'result_selection': self.result_selection,
            'period_length': self.period_length,
            'journal_ids': [a.id for a in self.env['account.journal'].search([])],
            'date_from': self.date_from,
        })
        used_context.update(
            {
                'state': self.target_move,
                'strict_range': True,
                'journal_ids': [a.id for a in self.env['account.journal'].search([])],
                'date_from': self.date_from

            }
        )
        data['form']['used_context'] = used_context
        data['form'].update(res)
        if not self._context.get('report_type') == 'excel':
            return self.env.ref('bi_partner_ledger_report.action_aged_partner_balance_report').with_context(
                landscape=True).report_action(self, data=data)
        else:
            filename = 'Aged Partner Balance.xls'
            workbook = xlwt.Workbook()
            worksheet = workbook.add_sheet('Sheet 1')
            self.excel_header(worksheet,res)

            date_format = xlwt.XFStyle()
            date_format.num_format_str = 'dd/mm/yyyy'
            style_header = xlwt.easyxf(
                "font:height 300; font: name Liberation Sans, bold on,color black; align: horiz center")
            style_table_header = xlwt.easyxf(
                "font: name Liberation Sans, bold on,color black; align: horiz center")

            row = 6
            col = 0
            count = 1
            report_values = self.env['report.bi_partner_ledger_report.bi_report_agedpartnerbalance']._get_report_values(
                self, data=data)
            if report_values['get_partner_lines']:
                worksheet.write(row, col, 'Account Total', style=style_table_header)
                worksheet.write(row, col + 1, report_values['get_direction'][6], style=style_table_header)
                worksheet.write(row, col + 2, report_values['get_direction'][4], style=style_table_header)
                worksheet.write(row, col + 3, report_values['get_direction'][3], style=style_table_header)
                worksheet.write(row, col + 4, report_values['get_direction'][2], style=style_table_header)
                worksheet.write(row, col + 5, report_values['get_direction'][1], style=style_table_header)
                worksheet.write(row, col + 6, report_values['get_direction'][0], style=style_table_header)
                worksheet.write(row, col + 7, report_values['get_direction'][5], style=style_table_header)
            row += 1
            for partner in report_values['get_partner_lines']:
                if row > 50000:
                    count += 1
                    worksheet = workbook.add_sheet('Sheet ' + str(count))
                    self.excel_header(worksheet)
                    row=6
                    col=0

                worksheet.write(row, col, partner['name'])
                worksheet.write(row, col + 1, partner['direction'])
                worksheet.write(row, col + 2, partner['4'])
                worksheet.write(row, col + 3, partner['3'])
                worksheet.write(row, col + 4, partner['2'])
                worksheet.write(row, col + 5, partner['1'])
                worksheet.write(row, col + 6, partner['0'])
                worksheet.write(row, col + 7, partner['total'])
                row += 1

            fp = io.BytesIO()
            workbook.save(fp)

            export_id = self.env['excel.report'].create(
                {'excel_file': base64.encodestring(fp.getvalue()), 'file_name': filename})
            res = {
                'view_mode': 'form',
                'res_id': export_id.id,
                'res_model': 'excel.report',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
            return res
