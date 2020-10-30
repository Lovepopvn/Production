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

_logger = logging.getLogger(__name__)


class VatDeclaration(models.TransientModel):
    _name = 'vat.declaration.report'

    report_type = fields.Selection([
        ('period', 'Period'),
        ('month', 'Month'),
        ('manual', 'Manual')
    ], string='View Report By', required=True)
    period = fields.Selection([
        ('Q1', 'Q1'),
        ('Q2', 'Q2'),
        ('Q3', 'Q3'),
        ('Q4', 'Q4'),
        ('Year', 'Year')
    ])
    month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')
    ])
    year = fields.Selection(
        selection='_compute_year_list',
        default=lambda self: time.strftime('%Y'), string='Year')
    start_date = fields.Date('Start')
    end_date = fields.Date('End')
    submission_time = fields.Selection(
        selection=lambda self: [(str(t + 1), str(t + 1)) for t in range(50)],
        string='Submission Time',
        required=True)
    data_x = fields.Binary('File', readonly=True)

    @api.onchange('report_type')
    def reset_value(self):
        self.period = False
        self.month = False
        self.start_date = False
        self.end_date = False

    def _compute_year_list(self):
        year = int(time.strftime('%Y'))
        return [((str(year + r)), (str(year + r))) for r in range(2000 - year, 11, 1)]

    def print_pdf(self):

        return self.env.ref('vn_vat_declaration.action_print_preview').report_action(self, data=self.combined_data())

    def field_validation(self):
        if self.start_date and self.end_date:
            start_date = self.start_date
            end_date = self.end_date
        elif self.month:
            month_length = monthrange(int(self.year), int(self.month))[1]
            start_date = datetime.strptime(self.year + '-' + self.month + '-1', '%Y-%m-%d').date()
            end_date = datetime.strptime(self.year + '-' + self.month + '-' + str(month_length), '%Y-%m-%d').date()
        elif self.period:
            if self.period == 'Q1':
                start_date = datetime.strptime(self.year + '-1-1', '%Y-%m-%d').date()
                end_date = datetime.strptime(self.year + '-3-31', '%Y-%m-%d').date()
            if self.period == 'Q2':
                start_date = datetime.strptime(self.year + '-4-1', '%Y-%m-%d').date()
                end_date = datetime.strptime(self.year + '-6-30', '%Y-%m-%d').date()
            if self.period == 'Q3':
                start_date = datetime.strptime(self.year + '-7-1', '%Y-%m-%d').date()
                end_date = datetime.strptime(self.year + '-9-30', '%Y-%m-%d').date()
            if self.period == 'Q4':
                start_date = datetime.strptime(self.year + '-10-1', '%Y-%m-%d').date()
                end_date = datetime.strptime(self.year + '-12-31', '%Y-%m-%d').date()
            if self.period == 'Year':
                start_date = datetime.strptime(self.year + '-1-1', '%Y-%m-%d').date()
                end_date = datetime.strptime(self.year + '-12-31', '%Y-%m-%d').date()
        else:
            raise UserError(_('You can not leave the field(s) blank'))
        if start_date > end_date:
            raise ValidationError(_('Start Date must be earlier than End Date!'))
        if self.report_type == 'manual':
            if start_date.month == end_date.month and start_date.year == end_date.year:
                name_month = month_name[start_date.month]
            else:
                name_month = month_name[start_date.month] + ' - ' + month_name[end_date.month]
        elif self.report_type == 'period':
            name_month = self.period
        else:
            name_month = month_name[start_date.month]
        return {'start_date': start_date, 'end_date': end_date, 'month_name': name_month, 'month_int':f'{start_date.month:02}'}

    def get_company_data(self):
        default_company = self.env['res.company']._company_default_get('vat.declaration.report')
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

    def data_exists(self, date_range):
        start_date = date_range['start_date']
        end_date = date_range['end_date']

        # query = """
        #     SELECT id
        #     FROM account_move
        #     WHERE (account_move.date BETWEEN '""" + start_date.strftime('%Y-%m-%d') + """' AND '""" + end_date.strftime('%Y-%m-%d') + """')
        # """
        query = f"""SELECT id
                    FROM account_move
                    WHERE (account_move.date BETWEEN '{start_date}' AND '{end_date}')"""

        print('--- date exists query ---', query)
        
        self.env.cr.execute(query)
        query_result = self.env.cr.dictfetchall()
        if not query_result:
            return False
        else:
            return True

    def combined_data(self):
        date_range = self.field_validation()

        all_data = {}

        date_range_previous = {}
        deltatime = date_range.get('start_date') - date_range.get('end_date')
        date_range_previous = date_range.copy()
        date_range_previous.update({
            'start_date':date_range.get('start_date') + timedelta(days=deltatime.days),
            'end_date':date_range.get('end_date') + timedelta(days=deltatime.days)
        })
        vat_in_config = self.env['vat.in.configuration'].search([('id','!=',False)]) #all config
        i_23_vat_configs = vat_in_config.filtered(lambda r:r.id!=5) # all except id 5,, use static id confirm by Loc
        i_40_b_vat_configs = vat_in_config.filtered(lambda r:r.id==4)

        all_data.update({
            'i_22': 0,
            'i_23': self.bill_before_tax(date_range),
            'i_24': self.tax_bill(date_range, "VAT value of goods and services purchased", "good_and_service", i_23_vat_configs),
            # 'i_25': self.tax_bill(date_range, "Total deducted VAT amount in in the period", "deducted"),
            'i_25': self.env['vat.allocation.report'].get_seventh_value(date_range),
            'i_26': self.invoice_before_tax(date_range, "non_taxable"),
            'i_29': self.invoice_before_tax(date_range, "0"),
            'i_30': self.invoice_before_tax(date_range, "5"),
            'i_31': self.tax_invoice(date_range, "5", ['out_invoice','out_refund']),
            'i_32': self.invoice_before_tax(date_range, "10"),
            'i_32a': self.invoice_before_tax(date_range, "tax_exempt"),
            'i_33': self.tax_invoice(date_range, "10", ('out_invoice','out_refund')),
            
            
            'i_37':0,
            'i_38':0,
            
            'i_39': 0,
            'i_40b': self.tax_bill(date_range, "VAT on the purchase of investment projects", "purchase_investment", i_40_b_vat_configs),
            'i_42': 0,
        })

        if not self.data_exists(date_range):
            all_data = dict.fromkeys(all_data, 0)
            all_data.update({'empty_data': True})
        else:
            all_data.update({'empty_data': False})

        all_data.update({
            'year': self.year,
            'report_type': self.report_type,
            'submission_time': self.submission_time,
            'day_today': datetime.today().strftime('%A'),
            'date_today': datetime.today().strftime('%d'),
            'month_today': datetime.today().strftime('%B'),
            'year_today': datetime.today().strftime('%Y'),
        })
        all_data.update(date_range)
        all_data.update(self.get_company_data())
        return all_data

    def get_report_file_name(self):
        report_name = 'VAT Declaration Report '
        if self.report_type == 'period':
            report_name += f'{self.period} {self.year}'
        if self.report_type == 'month':
            report_name += f'{month_name[int(self.month)]} {self.year}'
        if self.report_type == 'manual':
            report_name += f'{month_name[self.start_date.month]} - {month_name[self.end_date.month]} {self.year}'
        return report_name

    def _multi_company_cond(self):
        condition = ''
        company_ids = ','.join([str(id) for id in self.env.companies.ids])
        condition  = f"company_id IN ({company_ids})"
        return condition

    def tax_invoice(self, date_range, percentage, move_type='out_invoice'):
        start_date = date_range['start_date']
        end_date = date_range['end_date']
        dict_name = 'tax_invoice_total_' + percentage
        company_cond = 'account_move.'+self._multi_company_cond()

        if type(move_type) in (list,tuple):
            move_type_val = """in """+str(tuple(move_type))
        else:
            move_type_val = """= '"""+move_type+"""'"""

        query = """
            SELECT -sum(account_tax.amount*account_move_line.balance/100) as """ + dict_name + """
            FROM account_move
            LEFT JOIN account_move_line
            ON account_move.id = account_move_line.move_id
            LEFT JOIN account_move_line_account_tax_rel
            ON account_move_line.id = account_move_line_account_tax_rel.account_move_line_id
			LEFT JOIN account_tax
			ON account_tax.id = account_move_line_account_tax_rel.account_tax_id
            WHERE (account_move.invoice_date BETWEEN '""" + start_date.strftime('%Y-%m-%d') + """' AND '""" + end_date.strftime('%Y-%m-%d') + """')
            AND account_move.type """+move_type_val+"""
            AND account_tax.name = 'Thuế GTGT phải nộp """ + percentage + """%'
            AND account_move.state='posted'
            AND """+company_cond+""";
        """
        self.env.cr.execute(query)
        query_result = self.env.cr.dictfetchall()
        if query_result[0][dict_name] is None:
            query_result[0][dict_name] = 0
        return query_result[0][dict_name]

    def invoice_before_tax(self, date_range, percentage):
        start_date = date_range['start_date']
        end_date = date_range['end_date']
        company_cond = 'account_move.'+self._multi_company_cond()
        no_tax = False
        if percentage == 'No Tax':
            tax_name = 'No Tax'
            dict_name = 'invoice_before_tax_no_tax'
            no_tax = True

        elif percentage in ('non_taxable','tax_exempt'):
            tax_name = False
            dict_name = 'invoice_before_tax_%s' % percentage
            no_tax = True
        
        else:
            tax_name = 'Thuế GTGT phải nộp ' + percentage + '%'
            dict_name = 'invoice_before_tax_' + percentage
        
        tax_condition = ''
        if no_tax:
            if percentage=='No Tax':
                tax_condition = " AND account_tax.non_tax_type IS NOT NULL"
            elif percentage in ['non_taxable','tax_exempt']:
                tax_condition = " AND account_tax.non_tax_type = '"+percentage+"'"
        else:
            if tax_name:
                tax_condition = " AND account_tax.name = '"+tax_name+"'"

        query = """
            SELECT -sum(account_move_line.balance) AS """+dict_name+"""
            FROM account_move
            LEFT JOIN account_move_line
                ON account_move.id = account_move_line.move_id
            LEFT JOIN account_move_line_account_tax_rel
                ON account_move_line.id = account_move_line_account_tax_rel.account_move_line_id
			LEFT JOIN account_tax
			    ON account_tax.id = account_move_line_account_tax_rel.account_tax_id
            WHERE (account_move.invoice_date BETWEEN '"""+start_date.strftime('%Y-%m-%d')+"""' AND '"""+end_date.strftime('%Y-%m-%d')+"""')
            AND account_move.type in ('out_invoice','out_refund')
            """+tax_condition+""" 
            AND account_move.state='posted'
            AND """+company_cond+""";
        """ 

        self.env.cr.execute(query)
        query_result = self.env.cr.dictfetchall()
        if query_result[0][dict_name] is None:
            query_result[0][dict_name] = 0
        return query_result[0][dict_name]

    def bill_before_tax(self, date_range):
        start_date = date_range['start_date']
        end_date = date_range['end_date']
        dict_name = 'bill_before_tax'
        company_cond = 'account_move.'+self._multi_company_cond()

        query = """
            SELECT sum(account_move_line.balance) """ + dict_name + """
            FROM account_move
            LEFT JOIN account_move_line
            ON account_move.id = account_move_line.move_id
            WHERE (account_move.invoice_date BETWEEN '""" + start_date.strftime('%Y-%m-%d') + """' AND '""" + end_date.strftime('%Y-%m-%d') + """')
            AND account_move.type IN ('in_invoice','in_refund')
            AND account_move_line.vat_in_config_id IN (1, 2, 3, 4, 6)
            AND account_move_line.exclude_from_invoice_tab = False
            AND account_move_line.move_id IS NOT NULL AND account_move.state='posted'
            AND """+company_cond+""";
        """
        self.env.cr.execute(query)
        query_result = self.env.cr.dictfetchall()
        if query_result[0][dict_name] is None:
            query_result[0][dict_name] = 0
        return query_result[0][dict_name]

    def tax_bill(self, date_range, vat_declaration_name, name, vat_in_configs):
        start_date = date_range['start_date']
        end_date = date_range['end_date']
        dict_name = 'tax_bill_total_' + name
        company_cond = 'account_move_line.'+self._multi_company_cond()

        query = """
            SELECT sum(account_move_line.balance) """ + dict_name + """
            FROM account_move_line
            LEFT JOIN account_move
                ON account_move_line.move_id = account_move.id

            WHERE 
                account_move_line.vat_in_config_id in %s
                AND account_move.type IN ('in_invoice','in_refund')
			    AND account_move_line.tax_line_id IS NOT NULL
                AND (account_move.invoice_date BETWEEN '""" + start_date.strftime('%Y-%m-%d') + """' AND '""" + end_date.strftime('%Y-%m-%d') + """')
                AND account_move.state='posted'
                AND """+company_cond+""";
        """
        self.env.cr.execute(query, (tuple(vat_in_configs.ids),))
        query_result = self.env.cr.dictfetchall()
        if query_result[0][dict_name] is None:
            query_result[0][dict_name] = 0
        return query_result[0][dict_name]

    def credit_note_reversal(self, date_range, date_range_previous, state='posted'):
        note_type = 'out_refund'
        start_date = date_range['start_date']
        end_date = date_range['end_date']
        start_date_previous = date_range_previous.get('start_date')
        end_date_previous = date_range_previous.get('end_date')

        dict_name = 'tax_invoice_total_' + note_type

        query = """
            SELECT sum(account_tax.amount*account_move_line.price_subtotal/100) as """ + dict_name + """
            FROM account_move
            JOIN account_move as origin_invoice ON origin_invoice.id = account_move.reversed_entry_id
            LEFT JOIN account_move_line
            ON account_move.id = account_move_line.move_id
            LEFT JOIN account_move_line_account_tax_rel
            ON account_move_line.id = account_move_line_account_tax_rel.account_move_line_id
			LEFT JOIN account_tax
			ON account_tax.id = account_move_line_account_tax_rel.account_tax_id
            WHERE (account_move.invoice_date BETWEEN '""" + start_date.strftime('%Y-%m-%d') + """' AND '""" + end_date.strftime('%Y-%m-%d') + """')
            AND account_move.type = '""" + note_type + """'
            AND origin_invoice.invoice_date BETWEEN '""" + start_date_previous.strftime('%Y-%m-%d') + """' AND '""" + end_date_previous.strftime('%Y-%m-%d') + """'
        """

        if state:
            query += " AND account_move.state = '"+state+"'"
        
        self.env.cr.execute(query)
        query_result = self.env.cr.dictfetchall()
        if query_result[0][dict_name] is None:
            query_result[0][dict_name] = 0
        return query_result[0][dict_name]


    def tax_notes(self, date_range, note_type, state='posted', percentage=None):
        start_date = date_range['start_date']
        end_date = date_range['end_date']
        dict_name = 'tax_invoice_total_' + note_type

        query = """
            SELECT sum(account_tax.amount*account_move_line.price_subtotal/100) as """ + dict_name + """
            FROM account_move
            LEFT JOIN account_move_line
            ON account_move.id = account_move_line.move_id
            LEFT JOIN account_move_line_account_tax_rel
            ON account_move_line.id = account_move_line_account_tax_rel.account_move_line_id
			LEFT JOIN account_tax
			ON account_tax.id = account_move_line_account_tax_rel.account_tax_id
            WHERE (account_move.invoice_date BETWEEN '""" + start_date.strftime('%Y-%m-%d') + """' AND '""" + end_date.strftime('%Y-%m-%d') + """')
            AND account_move.type = '""" + note_type + """'
        """

        if percentage:
            if percentage in ['non_taxable','tax_exempt']:
                query += " AND account_tax.non_tax_type = '%s'" % (percentage,)
            else:
                tax_name = 'Thuế GTGT phải nộp ' + percentage + '%'
                query += " AND account_tax.name = '%s'" % (tax_name,)

        if state:
            query += " AND account_move.state = '"+state+"'"
        
        self.env.cr.execute(query)
        query_result = self.env.cr.dictfetchall()
        if query_result[0][dict_name] is None:
            query_result[0][dict_name] = 0
        return query_result[0][dict_name]

    def cancelled_invoice(self, date_range):
        start_date = date_range['start_date']
        end_date = date_range['end_date']
        dict_name = 'tax_cancelled_total'

        query = """
            SELECT sum(account_tax.amount*account_move_line.price_subtotal/100) as """ + dict_name + """
            FROM account_move
            LEFT JOIN account_move_line
            ON account_move.id = account_move_line.move_id
            LEFT JOIN account_move_line_account_tax_rel
            ON account_move_line.id = account_move_line_account_tax_rel.account_move_line_id
			LEFT JOIN account_tax
			ON account_tax.id = account_move_line_account_tax_rel.account_tax_id
            WHERE (account_move.invoice_date BETWEEN '""" + start_date.strftime('%Y-%m-%d') + """' AND '""" + end_date.strftime('%Y-%m-%d') + """')
            AND account_move.type = 'out_invoice'
            AND account_move.state = 'cancel';
        """
        self.env.cr.execute(query)
        query_result = self.env.cr.dictfetchall()
        if query_result[0][dict_name] is None:
            query_result[0][dict_name] = 0
        return query_result[0][dict_name]

    @api.onchange('report_type', 'period', 'month', 'start_date', 'end_date', 'year')
    def reset_xlsx_file(self):
        self.data_x = False

    def print_excel(self):
        '''function to generate excel report'''
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Declaration Report')
        filename = 'VAT Declaration Report.xlsx'
        excel_data = self.combined_data()

        # FORMAT
        format_left = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'font_name': 'Times New Roman'})
        format_center = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Times New Roman'})
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
        format_center_bordered_9 = workbook.add_format({
            'align': 'center',
            'border': 1,
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
            'font_size': 9})
        format_right_bordered = workbook.add_format({
            'align': 'right',
            'border': 1,
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
            'num_format': '#,##0 ₫'})
        format_bold_left = workbook.add_format({
            'bold': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_name': 'Times New Roman'})
        format_bold_center = workbook.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Times New Roman'})
        format_bold_left_bordered = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_name': 'Times New Roman'})
        format_bold_center_bordered = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Times New Roman'})
        format_italic_left = workbook.add_format({
            'italic': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_name': 'Times New Roman'})
        format_italic_center = workbook.add_format({
            'italic': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Times New Roman'})
        format_italic_right = workbook.add_format({
            'italic': 1,
            'align': 'right',
            'valign': 'vcenter',
            'font_name': 'Times New Roman'})
        format_bold_center_header = workbook.add_format({
            'bold': 1,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Times New Roman'})
        format_invisible = workbook.add_format({
            'font_color': '#ffffff'})

        # CELL SIZE
        worksheet.set_column('A:A', 5)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 14)
        worksheet.set_column('E:E', 6)
        worksheet.set_column('F:F', 4)
        worksheet.set_column('G:G', 6)
        worksheet.set_column('H:H', 5)
        worksheet.set_column('I:I', 15)
        worksheet.set_column('J:J', 5)
        worksheet.set_column('K:K', 15)
        worksheet.set_row(18, 26)

        # SET HEADER
        worksheet.merge_range('A1:B3', '', format_bold_center_header)
        worksheet.merge_range('C1:I1', '54r', format_bold_center_header)
        worksheet.merge_range('C2:I2', 'Độc lập - Tự do - Hạnh phúc', format_bold_center_header)
        worksheet.merge_range('C3:I3', 'TỜ KHAI THUẾ GIÁ TRỊ GIA TĂNG', format_bold_center_header)
        if excel_data['report_type'] == 'period':
            worksheet.merge_range('C5:I5', '[01] Kỳ tính thuế: Quý ' + excel_data['month_name'] + ' năm ' + excel_data['year'], format_bold_center)
        else:
            worksheet.merge_range('C5:I5', '[01] Kỳ tính thuế: Tháng ' + excel_data.get('month_int') + ' năm ' + excel_data['year'], format_bold_center)
        if excel_data['submission_time'] == '1':
            worksheet.merge_range('C6:I6', '[02] Lần đầu [' + excel_data['submission_time'] + ']                        [03] Bổ sung lần thứ [    ]', format_center)
        else:
            worksheet.merge_range('C6:I6', '[02] Lần đầu [    ]                        [03] Bổ sung lần thứ [' + excel_data['submission_time'] + ']', format_center)
        worksheet.merge_range('J1:K3', 'Mẫu số: 01-1/GTGT \n(Ban hành kèm theo Thông tư \n số 156/2013/TT-BTC ngày \n06/11/2013 của Bộ Tài chính)', format_center_bordered_9)
        worksheet.merge_range('B4:K4', '(Dành cho người nộp thuế khai thuế giá trị gia tăng theo phương pháp khấu trừ)', format_italic_center)
        worksheet.write('B7', '[04] Tên người nộp thuế:', format_bold_left)
        worksheet.write('B8', '[05] Mã số thuế:', format_bold_left)
        worksheet.write('B9', '[06] Địa chỉ:', format_bold_left)
        worksheet.write('B10', '[07] Quận/huyện:', format_bold_left)
        worksheet.write('D10', '[08] Tỉnh/thành phố:', format_bold_left)
        worksheet.write('B11', '[09] Điện thoại:', format_bold_left)
        worksheet.write('D11', '[10] Fax:', format_bold_left)
        worksheet.write('H11', '[11] E-mail:', format_bold_left)
        worksheet.write('B12', '[12] Tên đại lý thuế (nếu có):', format_bold_left)
        worksheet.write('B13', '[13] Mã số thuế:', format_bold_left)
        worksheet.write('B14', '[14] Địa chỉ:', format_bold_left)
        worksheet.write('B15', '[15] Quận/ huyện:', format_bold_left)
        worksheet.write('H15', '[16] Tỉnh/thành phố', format_bold_left)
        worksheet.write('B16', '[17] Điện thoại:', format_bold_left)
        worksheet.write('D16', '[18] Fax:', format_bold_left)
        worksheet.write('H16', '[19] E-mail:', format_bold_left)
        worksheet.write('B17', '[20] Hợp đồng đại lý thuế: Số', format_bold_left)
        worksheet.write('D17', 'Ngày:', format_bold_left)
        worksheet.merge_range('A18:K18', 'Đơn vị tiền: đồng Việt Nam', format_italic_right)
        # SET CONTENT - HEADER #
        worksheet.write('A19', 'STT', format_bold_center_bordered)
        worksheet.merge_range('B19:G19', 'Chỉ tiêu', format_bold_center_bordered)
        worksheet.merge_range('H19:I19', 'Giá trị HHDV \n (chưa có thuế GTGT)', format_bold_center_bordered)
        worksheet.merge_range('J19:K19', 'Thuế GTGT', format_bold_center_bordered)
        # SET CONTENT - TABLE (A) #
        worksheet.write('A20', 'A', format_bold_center_bordered)
        worksheet.write('A21', 'B', format_bold_center_bordered)
        worksheet.write('A22', 'C', format_bold_center_bordered)
        worksheet.write('A23', 'I', format_bold_center_bordered)
        worksheet.write('A24', '1', format_bold_center_bordered)
        worksheet.write('A25', '2', format_bold_center_bordered)
        worksheet.write('A26', 'II', format_bold_center_bordered)
        worksheet.write('A27', '1', format_bold_center_bordered)
        worksheet.write('A28', '2', format_bold_center_bordered)
        worksheet.write('A29', 'a', format_bold_center_bordered)
        worksheet.write('A30', 'b', format_bold_center_bordered)
        worksheet.write('A31', 'c', format_bold_center_bordered)
        worksheet.write('A32', 'd', format_bold_center_bordered)
        worksheet.write('A33', '3', format_bold_center_bordered)
        worksheet.write('A34', 'III', format_bold_center_bordered)
        worksheet.write('A35', 'IV', format_bold_center_bordered)
        worksheet.write('A36', '1', format_bold_center_bordered)
        worksheet.write('A37', '2', format_bold_center_bordered)
        worksheet.write('A38', 'V', format_bold_center_bordered)
        worksheet.write('A39', 'VI', format_bold_center_bordered)
        worksheet.write('A40', '1', format_bold_center_bordered)
        worksheet.write('A41', '2', format_bold_center_bordered)
        worksheet.write('A42', '3', format_bold_center_bordered)
        worksheet.write('A43', '4', format_bold_center_bordered)
        worksheet.write('A44', '4.1', format_bold_center_bordered)
        worksheet.write('A45', '4.2', format_bold_center_bordered)
        # SET CONTENT - TABLE (B) #
        worksheet.merge_range('B20:E20', 'Không phát sinh hoạt động mua, bán trong kỳ (đánh dấu "X")', format_bold_left_bordered)
        worksheet.merge_range('B21:I21', 'Thuế GTGT còn được khấu trừ kỳ trước chuyển sang', format_bold_left_bordered)
        worksheet.merge_range('B22:K22', 'Kê khai thuế GTGT phải nộp Ngân sách nhà nước', format_bold_left_bordered)
        worksheet.merge_range('B23:K23', 'Hàng hoá, dịch vụ (HHDV) mua vào trong kỳ', format_bold_left_bordered)
        worksheet.merge_range('B24:G24', 'Giá trị và thuế GTGT của hàng hoá, dịch vụ mua vào', format_left_bordered)
        worksheet.merge_range('B25:I25', 'Tổng số thuế GTGT được khấu trừ kỳ này', format_left_bordered)
        worksheet.merge_range('B26:K26', 'Hàng hoá, dịch vụ bán ra trong kỳ', format_bold_left_bordered)
        worksheet.merge_range('B27:G27', 'Hàng hóa, dịch vụ bán ra không chịu thuế GTGT', format_left_bordered)
        worksheet.merge_range('B28:G28', 'Hàng hóa, dịch vụ bán ra chịu thuế GTGT ([27]=[29]+[30]+[32]+[32a]; [28]=[31]+[33])', format_left_bordered)
        worksheet.merge_range('B29:G29', 'Hàng hoá, dịch vụ bán ra chịu thuế suất 0%', format_left_bordered)
        worksheet.merge_range('B30:G30', 'Hàng hoá, dịch vụ bán ra chịu thuế suất 5%', format_left_bordered)
        worksheet.merge_range('B31:G31', 'Hàng hoá, dịch vụ bán ra chịu thuế suất 10%', format_left_bordered)
        worksheet.merge_range('B32:G32', 'Hàng hoá, dịch vụ bán ra không tính thuế', format_left_bordered)
        worksheet.merge_range('B33:G33', 'Tổng doanh thu và thuế GTGT của HHDV bán ra ([34]=[26]+[27]; [35]=[28])', format_left_bordered)
        worksheet.merge_range('B34:I34', 'Thuế GTGT phát sinh trong kỳ ([36]=[35]-[25])', format_bold_left_bordered)
        worksheet.merge_range('B35:K35', 'Điều chỉnh tăng, giảm thuế GTGT còn được khấu trừ của các kỳ trước', format_bold_left_bordered)
        worksheet.merge_range('B36:I36', 'Điều chỉnh giảm', format_left_bordered)
        worksheet.merge_range('B37:I37', 'Điều chỉnh tăng', format_left_bordered)
        worksheet.merge_range('B38:I38', 'Thuế GTGT đã nộp ở địa phương khác của hoạt động kinh doanh xây dựng, lắp đặt, bán hàng, bất động sản ngoại tỉnh', format_bold_left_bordered)
        worksheet.merge_range('B39:K39', 'Xác định nghĩa vụ thuế GTGT phải nộp trong kỳ:', format_bold_left_bordered)
        worksheet.merge_range('B40:I40', 'Thuế GTGT phải nộp của hoạt động sản xuất kinh doanh trong kỳ ([40a]=[36]-[22]+[37]-[38] - [39]≥ 0)', format_bold_left_bordered)
        worksheet.merge_range('B41:I41', 'Thuế GTGT mua vào của dự án đầu tư được bù trừ với thuế GTGT còn phải nộp của hoạt động sản xuất kinh doanh cùng kỳ tính thuế', format_bold_left_bordered)
        worksheet.merge_range('B42:I42', 'Thuế GTGT còn phải nộp trong kỳ ([40]=[40a]-[40b])', format_bold_left_bordered)
        worksheet.merge_range('B43:I43', 'Thuế GTGT chưa khấu trừ hết kỳ này (nếu [41]=[36]-[22]+[37]-[38]-[39]< 0)', format_bold_left_bordered)
        worksheet.merge_range('B44:I44', 'Tổng số thuế GTGT đề nghị hoàn', format_bold_left_bordered)
        worksheet.merge_range('B45:I45', 'Thuế GTGT còn được khấu trừ chuyển kỳ sau ([43]=[41]-[42])', format_bold_left_bordered)
        # SET CONTENT - TABLE (NUMBERED) #
        worksheet.write('F20', '[21]', format_bold_center_bordered)
        worksheet.merge_range('H20:K20', '', format_bold_center_bordered)
        worksheet.write('H24', '[23]', format_bold_center_bordered)
        worksheet.write('H27', '[26]', format_bold_center_bordered)
        worksheet.merge_range('J27:K27', '', format_bold_center_bordered)
        worksheet.write('H28', '[27]', format_bold_center_bordered)
        worksheet.write('H29', '[29]', format_bold_center_bordered)
        worksheet.merge_range('J29:K29', '', format_bold_center_bordered)
        worksheet.write('H30', '[30]', format_bold_center_bordered)
        worksheet.write('H31', '[32]', format_bold_center_bordered)
        worksheet.write('H32', '[32a]', format_bold_center_bordered)
        worksheet.merge_range('J32:K32', '', format_bold_center_bordered)
        worksheet.write('H33', '[34]', format_bold_center_bordered)
        worksheet.write('J21', '[22]', format_bold_center_bordered)
        worksheet.write('J24', '[24]', format_bold_center_bordered)
        worksheet.write('J25', '[25]', format_bold_center_bordered)
        worksheet.write('J28', '[28]', format_bold_center_bordered)
        worksheet.write('J30', '[31]', format_bold_center_bordered)
        worksheet.write('J31', '[33]', format_bold_center_bordered)
        worksheet.write('J33', '[35]', format_bold_center_bordered)
        worksheet.write('J34', '[36]', format_bold_center_bordered)
        worksheet.write('J36', '[37]', format_bold_center_bordered)
        worksheet.write('J37', '[38]', format_bold_center_bordered)
        worksheet.write('J38', '[39]', format_bold_center_bordered)
        worksheet.write('J40', '[40a]', format_bold_center_bordered)
        worksheet.write('J41', '[40b]', format_bold_center_bordered)
        worksheet.write('J42', '[40]', format_bold_center_bordered)
        worksheet.write('J43', '[41]', format_bold_center_bordered)
        worksheet.write('J44', '[42]', format_bold_center_bordered)
        worksheet.write('J45', '[43]', format_bold_center_bordered)

        # SET TABLE HEADER VALUE #
        worksheet.write('C7', excel_data['company_name'], format_bold_left)
        worksheet.write('C8', excel_data['tax_code'], format_bold_left)
        worksheet.write('C9', excel_data['address'], format_bold_left)
        worksheet.write('C10', excel_data['distric'], format_bold_left)
        worksheet.write('C11', excel_data['phone'], format_bold_left)
        worksheet.write('F10', excel_data['city'], format_bold_left)
        worksheet.write('J11', excel_data['email'], format_bold_left)

        # SET BODY VALUE #

        if excel_data['empty_data']:
            worksheet.write('G20', 'X', format_bold_center_bordered)                    # 21
        worksheet.write('K21', excel_data['i_22'], format_right_bordered)               # 22
        worksheet.write('I24', excel_data['i_23'], format_right_bordered)               # 23
        worksheet.write('K24', excel_data['i_24'], format_right_bordered)               # 24
        worksheet.write('K25', excel_data['i_25'], format_right_bordered)               # 25
        worksheet.write('I27', excel_data['i_26'], format_right_bordered)               # 26
        worksheet.write_formula('I28', '=SUM(I29:I31)', format_right_bordered)          # 27
        worksheet.write_formula('K28', '=SUM(K30:K31)', format_right_bordered)          # 28
        worksheet.write('I29', excel_data['i_29'], format_right_bordered)               # 29
        worksheet.write('I30', excel_data['i_30'], format_right_bordered)               # 30
        worksheet.write('K30', excel_data['i_31'], format_right_bordered)               # 31
        worksheet.write('I31', excel_data['i_32'], format_right_bordered)               # 32
        worksheet.write('I32', excel_data['i_32a'], format_right_bordered)              # 32a
        worksheet.write('K31', excel_data['i_33'], format_right_bordered)               # 33
        worksheet.write_formula('I33', '=I27+I28', format_right_bordered)               # 34
        worksheet.write_formula('K33', '=K28', format_right_bordered)                   # 35
        worksheet.write_formula('K34', '=K33-K25', format_right_bordered)               # 36
        worksheet.write('K36', excel_data['i_37'], format_right_bordered)               # 37
        worksheet.write('K37', excel_data['i_38'], format_right_bordered)               # 38
        worksheet.write('K38', excel_data['i_39'], format_right_bordered)               # 39
        worksheet.write_formula('K40', '=K34-K212+K36-K37-K38', format_right_bordered)  # 40a
        worksheet.write('K41', excel_data['i_40b'], format_right_bordered)              # 40b
        worksheet.write_formula('K42', '=K40-K41', format_right_bordered)               # 40
        worksheet.write_formula('K43', '=K34-K212+K36-K37-K38', format_right_bordered)  # 41
        worksheet.write('K44', excel_data['i_42'], format_right_bordered)               # 42
        worksheet.write_formula('K45', '=K43-K44', format_right_bordered)               # 43

        # Conditional
        worksheet.conditional_format('K40', {
            'type': 'cell',
            'criteria': '<',
            'value': 0,
            'format': format_invisible,
        })

        worksheet.conditional_format('K43', {
            'type': 'cell',
            'criteria': '>=',
            'value': 0,
            'format': format_invisible,
        })

        # SET FOOTER #
        day = excel_data['day_today']
        date = excel_data['date_today']
        month = excel_data['month_today']
        year = excel_data['year_today']
        print_date = day + ', ' + date + ' ' + month + ' ' + year
        worksheet.merge_range('D47:K47', print_date, format_italic_center)
        worksheet.write('B46', 'Tôi cam đoan số liệu khai trên là đúng và chịu trách nhiệm trước pháp luật về những số liệu đã khai./.', format_left)
        worksheet.write('B48', 'NHÂN VIÊN ĐẠI LÝ THUẾ', format_bold_left)
        worksheet.write('B49', 'Họ và tên:', format_left)
        worksheet.write('B50', 'Chứng chỉ hành nghề số:', format_left)
        worksheet.merge_range('D48:K48', 'NGƯỜI NỘP THUẾ hoặc', format_bold_center)
        worksheet.merge_range('D49:K49', 'ĐẠI DIỆN HỢP PHÁP CỦA NGƯỜI NỘP THUẾ', format_bold_center)
        worksheet.merge_range('D50:K50', '(Ký, ghi rõ họ tên; chức vụ và đóng dấu (nếu có))', format_center)
        worksheet.write('B54', 'Ghi chú:', format_bold_left)
        worksheet.write('B55', '- GTGT: Giá trị Gia tăng', format_left)
        worksheet.write('B56', '- HHDV: Hàng hoá dịch vụ', format_left)

        #########################

        workbook.close()
        output.seek(0)
        out = base64.encodestring(output.getvalue())
        self.write({
            'data_x': out})
        return {
            'type': 'ir.actions.act_url',
            'url': '/vat_allocation_download?model=vat.declaration.report&id=%s&filename=VAT_Declaration_Report' % (self.id),
            'target': 'self',
        }
