from calendar import monthrange, month_name
from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO
from odoo import api, fields, models, tools, _
from odoo.exceptions import Warning, ValidationError, UserError
import base64
import logging
import time
import xlsxwriter

from pprint import pprint

_logger = logging.getLogger(__name__)

Q1 = ['January', 'February', 'March']
Q2 = ['April', 'May', 'June']
Q3 = ['July', 'August', 'September']
Q4 = ['October', 'November', 'December']


class VatAllocation(models.TransientModel):
    _name = 'vat.allocation.report'

    start_date = fields.Date('Start')
    end_date = fields.Date('End')
    note = fields.Text()

    this_year = time.strftime('%Y')
    this_month = time.strftime('%B')
    this_month_number = int(time.strftime('%m'))
    this_quarter = ''
    last_year = str(int(this_year) - 1)
    if this_month_number == 1:
        last_month_number = 12
    else:
        last_month_number = this_month_number - 1
    last_month = month_name[last_month_number]

    data_x = fields.Binary('File', readonly=True)

    def _get_filter_name(name):
        this_year = time.strftime('%Y')
        this_month = time.strftime('%B')
        this_month_number = int(time.strftime('%m'))
        last_year = str(int(this_year) - 1)
        if this_month_number == 1:
            last_month_number = 12
        else:
            last_month_number = this_month_number - 1
        last_month = month_name[last_month_number]
        if name == 'this_year':
            return f'This year: {this_year}'
        elif name == 'this_quarter':
            if this_month in Q1:
                return f'Q1 {this_year}'
            if this_month in Q2:
                return f'Q2 {this_year}'
            if this_month in Q3:
                return f'Q3 {this_year}'
            if this_month in Q4:
                return f'Q3 {this_year}'
        elif name == 'this_month':
            return f'{this_month} {this_year}'
        elif name == 'last_month':
            if last_month_number == 12:
                return f'{last_month} {last_year}'
            else:
                return f'{last_month} {this_year}'
        elif name == 'last_quarter':
            if this_month in Q1:
                return f'Q4 {last_year}'
            if this_month in Q2:
                return f'Q1 {this_year}'
            if this_month in Q3:
                return f'Q2 {this_year}'
            if this_month in Q4:
                return f'Q4 {this_year}'
        elif name == 'last_year':
            return f'Last year: {last_year}'

    date_filter = fields.Selection([
        ('this_year', _get_filter_name('this_year')),
        ('this_quarter', _get_filter_name('this_quarter')),
        ('this_month', _get_filter_name('this_month')),
        ('last_month', _get_filter_name('last_month')),
        ('last_quarter', _get_filter_name('last_quarter')),
        ('last_year', _get_filter_name('last_year')),
        ('custom', 'Custom'),
    ], default='this_year', required=True)

    def _compute_date_range(self):
        start_date = end_date = None
        if self.start_date and self.end_date:
            start_date = self.start_date
            end_date = self.end_date
        elif self.date_filter == 'this_month':
            month_length = monthrange(int(self.this_year), self.this_month_number)[1]
            start_date = f'{self.this_year}-{self.this_month_number}-1'
            end_date = f'{self.this_year}-{self.this_month_number}-{month_length}'
        elif self.date_filter == 'this_quarter':
            if self.this_month in Q1:
                start_date = f'{self.this_year}-1-1'
                end_date = f'{self.this_year}-3-31'
            if self.this_month in Q2:
                start_date = f'{self.this_year}-4-1'
                end_date = f'{self.this_year}-6-30'
            if self.this_month in Q3:
                start_date = f'{self.this_year}-7-1'
                end_date = f'{self.this_year}-9-30'
            if self.this_month in Q4:
                start_date = f'{self.this_year}-10-1'
                end_date = f'{self.this_year}-12-31'
        elif self.date_filter == 'this_year':
            start_date = f'{self.this_year}-1-1'
            end_date = f'{self.this_year}-12-31'
        elif self.date_filter == 'last_month':
            if self.last_month_number == 12:
                this_year = self.last_year
            else:
                this_year = self.this_year
            month_length = monthrange(int(this_year), self.last_month_number)[1]
            start_date = f'{this_year}-{self.last_month_number}-1'
            end_date = f'{this_year}-{self.last_month_number}-{month_length}'
        elif self.date_filter == 'last_quarter':
            if self.this_month in Q1:
                start_date = f'{self.last_year}-10-1'
                end_date = f'{self.last_year}-12-31'
            if self.this_month in Q2:
                start_date = f'{self.this_year}-1-1'
                end_date = f'{self.this_year}-3-31'
            if self.this_month in Q3:
                start_date = f'{self.this_year}-4-1'
                end_date = f'{self.this_year}-6-30'
            if self.this_month in Q4:
                start_date = f'{self.this_year}-7-1'
                end_date = f'{self.this_year}-9-30'
        elif self.date_filter == 'last_year':
            start_date = f'{self.last_year}-1-1'
            end_date = f'{self.last_year}-12-31'

        if not start_date or not end_date:
            raise UserError(_('You can not leave the field(s) blank'))

        if isinstance(start_date, str):
            start_date = fields.Date.to_date(start_date)
        if isinstance(end_date, str):
            end_date = fields.Date.to_date(end_date)

        if start_date > end_date:
            raise ValidationError(_('Start Date must be earlier than End Date!'))

        start_date = fields.Date.to_string(start_date)
        end_date = fields.Date.to_string(end_date)
        return start_date, end_date

    def get_company_data(self):
        default_company = self.env['res.company']._company_default_get('vat.allocation.report')
        company_data = {
            'company_name': default_company.display_name,
            'tax_code': default_company.vat,
            'address': default_company.street,
            'distric': default_company.street2,
            'city': default_company.city,
            'phone': default_company.phone,
            'email': default_company.email
        }
        return company_data
    
    def _multi_company_cond(self):
        condition = ''
        company_ids = ','.join([str(id) for id in self.env.companies.ids])
        condition  = f"company_id IN ({company_ids})"
        return condition

    def invoice_before_tax(self, start_date, end_date):
        dict_name = 'invoice_before_tax'
        company_cond = 'account_move.'+self._multi_company_cond()

        # query = """
        #     SELECT sum(amount_untaxed) """ + dict_name + """
        #     FROM account_move
        #     WHERE (account_move.date BETWEEN '""" + start_date.strftime('%Y-%m-%d') + """' AND '""" + end_date.strftime('%Y-%m-%d') + """')
        #     AND account_move.type = 'out_invoice'
        # """

        query = f"""SELECT sum(amount_untaxed_signed) {dict_name}
                    FROM account_move
                    WHERE (account_move.date BETWEEN '{start_date}' AND '{end_date}')
                          AND account_move.type in ('out_invoice','out_refund') AND account_move.state='posted' AND {company_cond}"""

        self.env.cr.execute(query)
        query_result = self.env.cr.dictfetchall()
        if query_result[0][dict_name] is None:
            query_result[0][dict_name] = 0
        return query_result[0][dict_name]

    def taxed_invoice_before_tax(self, start_date, end_date):
        dict_name = 'taxed_invoice_before_tax'
        company_cond = 'am.'+self._multi_company_cond()
        

        query = f"""SELECT -sum(aml.balance) {dict_name}
                    FROM account_move am
                        LEFT JOIN account_move_line aml ON am.id = aml.move_id
                        LEFT JOIN account_move_line_account_tax_rel aml_tax ON aml.id = aml_tax.account_move_line_id
                    WHERE (am.date BETWEEN '{start_date}' AND '{end_date}')
                        AND am.type in ('out_invoice','out_refund')
                        AND am.state = 'posted'
                        AND {company_cond}
                        AND aml_tax.account_tax_id in (SELECT id
                                                   FROM account_tax
                                                   WHERE name='Thuế GTGT phải nộp 0%'
                                                   OR name='Thuế GTGT phải nộp 5%'
                                                   OR name='Thuế GTGT phải nộp 10%');"""

        self.env.cr.execute(query)
        query_result = self.env.cr.dictfetchall()
        if query_result[0][dict_name] is None:
            query_result[0][dict_name] = 0
        return query_result[0][dict_name]

    def taxed_journal_item_4(self, start_date, end_date):
        dict_name = 'taxed_journal_item_4'

        # query = """
        #     SELECT sum(account_move_line.debit) """ + dict_name + """
        #     FROM account_move_line
        #     LEFT JOIN account_move_line_account_tax_rel
        #     ON account_move_line_account_tax_rel.account_move_line_id = account_move_line.id
        #     WHERE (account_move_line.date BETWEEN '""" + start_date.strftime('%Y-%m-%d') + """' AND '""" + end_date.strftime('%Y-%m-%d') + """')
        #     AND account_move_line.purchased_vat_category = 3
        #     AND account_move_line_account_tax_rel.account_tax_id IS NOT NULL
        # """

        vat_in = self.env.ref('vn_vat_report.default_vat_in_config_03')

        account_1331 = self.env['account.account'].search([('code','=','1331')], limit=1).id or 'NULL'
        company_cond = 'aml.'+self._multi_company_cond()

        query = f"""SELECT sum(aml.balance) {dict_name}
                    FROM account_move_line aml
                         LEFT JOIN account_move_line_account_tax_rel aml_tax ON aml_tax.account_move_line_id = aml.id
                    WHERE (aml.date BETWEEN '{start_date}' AND '{end_date}')
                          AND {company_cond}
                          AND aml.vat_in_config_id = {vat_in.id}
                          AND aml.parent_state='posted'
                          AND aml.account_id = {account_1331}"""

        self.env.cr.execute(query)
        query_result = self.env.cr.dictfetchall()
        if query_result[0][dict_name] is None:
            query_result[0][dict_name] = 0
        return query_result[0][dict_name]

    def taxed_journal_item_6(self, start_date, end_date):
        dict_name = 'taxed_journal_item_6'

        # query = """
        #     SELECT sum(account_move_line.debit) """ + dict_name + """
        #     FROM account_move_line
        #     LEFT JOIN account_move_line_account_tax_rel
        #     ON account_move_line_account_tax_rel.account_move_line_id = account_move_line.id
        #     WHERE (account_move_line.date BETWEEN '""" + start_date.strftime('%Y-%m-%d') + """' AND '""" + end_date.strftime('%Y-%m-%d') + """')
        #     AND account_move_line.purchased_vat_category in (1, 4)
        #     AND account_move_line_account_tax_rel.account_tax_id IS NOT NULL
        # """

        vat_in_1 = self.env.ref('vn_vat_report.default_vat_in_config_01')
        vat_in_4 = self.env.ref('vn_vat_report.default_vat_in_config_04')
        account_1331 = self.env['account.account'].search([('code','=','1331')], limit=1).id or 'NULL'
        company_cond = 'aml.'+self._multi_company_cond()

        query = f"""SELECT sum(aml.balance) {dict_name}
                    FROM account_move_line aml
                         LEFT JOIN account_move_line_account_tax_rel aml_tax 
                            ON aml_tax.account_move_line_id = aml.id
                    WHERE (aml.date BETWEEN '{start_date}' AND '{end_date}')
                          AND aml.vat_in_config_id in ({vat_in_1.id}, {vat_in_4.id})
                          AND aml.account_id = {account_1331}
                          AND aml.parent_state='posted'
                          AND {company_cond}
                """

        self.env.cr.execute(query)
        query_result = self.env.cr.dictfetchall()
        if query_result[0][dict_name] is None:
            query_result[0][dict_name] = 0
        return query_result[0][dict_name]

    def combined_data(self):
        start_date, end_date = self._compute_date_range()
        i_01 = self.invoice_before_tax(start_date, end_date)
        i_02 = self.taxed_invoice_before_tax(start_date, end_date)
        i_03 = 0.0
        try:
            i_03 = float(i_02/i_01)
        except:
            pass
        # i_03 = 3.1

        all_data = {
            'start_date': start_date,
            'end_date': end_date,
            'i_01': i_01,
            'i_02': i_02,
            'i_03': i_03,
            'i_04': self.taxed_journal_item_4(start_date, end_date),
            'i_06': self.taxed_journal_item_6(start_date, end_date),
            'note': self.note
        }

        all_data.update(self.get_company_data())
        return all_data

    def print_pdf(self):
        combined_data = self.combined_data()
        pprint(combined_data)
        return self.env.ref('vn_vat_declaration.action_print_allocation').report_action(self, data=combined_data)

    def get_seventh_value(self, date_range):
        start_date = fields.Date.to_string(date_range['start_date'])
        end_date = fields.Date.to_string(date_range['end_date'])
        i_01 = int(self.invoice_before_tax(start_date, end_date))
        i_02 = int(self.taxed_invoice_before_tax(start_date, end_date))

        i_03 = i_02 / i_01 if i_01 else 1
        i_04 = int(self.taxed_journal_item_4(start_date, end_date))
        i_05 = i_04 * i_03
        i_06 = int(self.taxed_journal_item_6(start_date, end_date))
        i_07 = i_05 + i_06
        return i_07

    def print_excel(self):
        '''function to generate excel report'''
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Allocation Report')
        filename = 'VAT Allocation Report.xlsx'
        excel_data = self.combined_data()

        # FORMAT
        # format_left = workbook.add_format({
        #     'align': 'left',
        #     'valign': 'vcenter',
        #     'font_name': 'Times New Roman'})
        # format_center = workbook.add_format({
        #     'align': 'center',
        #     'valign': 'vcenter',
        #     'font_name': 'Times New Roman'})
        format_left_bordered = workbook.add_format({
            'align': 'left',
            'border': 1,
            'valign': 'vcenter',
            'font_name': 'Times New Roman'})
        format_center_bordered = workbook.add_format({
            'align': 'center',
            'border': 1,
            'valign': 'vcenter',
            'font_name': 'Times New Roman'})
        # format_center_bordered_9 = workbook.add_format({
        #     'align': 'center',
        #     'border': 1,
        #     'valign': 'vcenter',
        #     'font_name': 'Times New Roman',
        #     'font_size': 9})
        format_right_bordered = workbook.add_format({
            'align': 'right',
            'border': 1,
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
            'num_format': '#,##0 ₫'})
        format_right_bordered_decimal = workbook.add_format({
            'align': 'right',
            'border': 1,
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
            'num_format': '#,##0.00 ₫'})
        # format_bold_left = workbook.add_format({
        #     'bold': 1,
        #     'align': 'left',
        #     'valign': 'vcenter',
        #     'font_name': 'Times New Roman'})
        # format_bold_center = workbook.add_format({
        #     'bold': 1,
        #     'align': 'center',
        #     'valign': 'vcenter',
        #     'font_name': 'Times New Roman'})
        # format_bold_left_bordered = workbook.add_format({
        #     'bold': 1,
        #     'border': 1,
        #     'align': 'left',
        #     'valign': 'vcenter',
        #     'font_name': 'Times New Roman'})
        format_bold_center_bordered = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Times New Roman'})
        # format_italic_left = workbook.add_format({
        #     'italic': 1,
        #     'align': 'left',
        #     'valign': 'vcenter',
        #     'font_name': 'Times New Roman'})
        # format_italic_center = workbook.add_format({
        #     'italic': 1,
        #     'align': 'center',
        #     'valign': 'vcenter',
        #     'font_name': 'Times New Roman'})
        # format_italic_right = workbook.add_format({
        #     'italic': 1,
        #     'align': 'right',
        #     'valign': 'vcenter',
        #     'font_name': 'Times New Roman'})
        # format_bold_center_header = workbook.add_format({
        #     'bold': 1,
        #     'font_size': 14,
        #     'align': 'center',
        #     'valign': 'vcenter',
        #     'font_name': 'Times New Roman'})
        # format_invisible = workbook.add_format({
        #     'font_color': '#ffffff'})
        format_header_big = workbook.add_format({
            'font_size': 20,
        })

        # CELL SIZE
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 100)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 15)
        worksheet.set_row(1, 30)
        # worksheet.set_row(18, 26)

        # SET HEADER
        worksheet.merge_range('B2:C2', '')
        worksheet.merge_range('C5:C6', '')
        worksheet.write('B2', 'VAT Allocation Report', format_header_big)
        worksheet.write('B3', excel_data['company_name'])
        worksheet.write('B5', 'Note')
        worksheet.write('B8', 'Mã chỉ tiêu', format_bold_center_bordered)
        worksheet.write('B9', '1', format_center_bordered)
        worksheet.write('B10', '2', format_center_bordered)
        worksheet.write('B11', '3', format_center_bordered)
        worksheet.write('B12', '4', format_center_bordered)
        worksheet.write('B13', '5', format_center_bordered)
        worksheet.write('B14', '6', format_center_bordered)
        worksheet.write('B15', '7', format_center_bordered)
        if excel_data['note']:
            worksheet.write('C5', excel_data['note'])
        worksheet.write('C8', 'Chỉ tiêu', format_bold_center_bordered)
        worksheet.write('C9', 'Tổng Doanh thu bán ra', format_left_bordered)
        worksheet.write('C10', 'Doanh thu hoạt động chịu thuế GTGT (0%, 5%, 10%)', format_left_bordered)
        worksheet.write('C11', 'Tỷ lệ DT bán ra chịu thuế GTGT so với tổng DT', format_left_bordered)
        worksheet.write('C12', 'Thuế GTGT mua vào cần phân bổ (dùng chung cho hoạt động chịu thuế và không chịu thuế)', format_left_bordered)
        worksheet.write('C13', 'Thuế GTGT được khấu trừ phân bổ trong kỳ', format_left_bordered)
        worksheet.write('C14', 'Thuế GTGT dùng riêng cho hoạt động SXKD', format_left_bordered)
        worksheet.write('C15', 'Thuế GTGT được khấu trừ', format_left_bordered)
        worksheet.write('D8', 'Số tiền', format_bold_center_bordered)
        worksheet.write('D9', excel_data['i_01'], format_right_bordered)        # [1]
        worksheet.write('D10', excel_data['i_02'], format_right_bordered)       # [2]
        # worksheet.write_formula('D11', '=D10/D9', format_right_bordered)        # [3]
        worksheet.write('D11', excel_data['i_03'], format_right_bordered_decimal)       # [3]
        worksheet.write('D12', excel_data['i_04'], format_right_bordered)       # [4]
        worksheet.write_formula('D13', '=D11*D12', format_right_bordered)       # [5]
        worksheet.write('D14', excel_data['i_06'], format_right_bordered)       # [6]
        worksheet.write_formula('D15', '=D13+D14', format_right_bordered)       # [7]

        #########################

        workbook.close()
        output.seek(0)
        # out = base64.encodestring(output.getvalue())
        out = base64.encodebytes(output.getvalue())
        self.write({
            'data_x': out,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/vat_allocation_download?model=vat.allocation.report&id={self.id}&filename={filename}',
            'target': 'self',
        }
