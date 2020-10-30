# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields
from odoo.tools.translate import _
from odoo.tools.misc import formatLang, format_date
from datetime import datetime, timedelta
import io

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter

import pprint
pp = pprint.PrettyPrinter(indent=4)


class vat_out_report(models.AbstractModel):
    _inherit = 'account.generic.tax.report'
    _name = 'account.vat.out.report'
    _description = 'VAT Out Report'

    filter_date = {'date_from': '', 'date_to': '', 'filter': 'this_year'}
    # filter_cash_basis = False
    filter_comparison = None
    filter_unfold_all = False
    filter_all_entries = None
    filter_invoice_number = False
    filter_display_invoice_number = True
    # filter_account_type = [{'id': 'receivable', 'name': _('Receivable'), 'selected': False}, {'id': 'payable', 'name': _('Payable'), 'selected': False}]
    
    filter_partner = True
    filter_report_vat_in_out = True
    filter_vat_number = False

    def _get_columns_name(self, options):
        options['report_vat_in_out'] = 'vat_out'
        return [
            {'name': _('')},
            # {'name': _('Sequence number')},
            {'name': _('Số hoá đơn')},
            {'name': _('Ngày phát hành'), 'class': 'date'},
            {'name': _('Tên người mua')},
            {'name': _('Mã số thuế người mua')},
            {'name': _('Mặt hàng')},
            {'name': _('Doanh số bán chưa có thuế GTGT'), 'class': 'number'},
            {'name': _('Thuế GTGT'), 'class': 'number'},
            {'name': _('Ghi chú')},
        ]

    @api.model
    def _get_report_name(self):
        return _("Sales VAT Report")
    
    def _get_amlids_by_tax(self, tax_id):
        self._cr.execute("""SELECT account_move_line_account_tax_rel.account_move_line_id
                FROM account_move_line_account_tax_rel
                INNER JOIN account_tax 
                ON account_move_line_account_tax_rel.account_tax_id = account_tax.id
                WHERE account_tax.id = %s""",(tax_id.id,))
        amls = self._cr.dictfetchall()
        lista = []
        for aml in amls:
            lista.append(aml.get('account_move_line_id'))
        
        return lista

    def _get_aml_by_tax(self, options, tax_id):
        company_id = self.env.user.company_id
        #cond = [options['date']['date_from'], options['date']['date_from'], options['date']['date_to'], options['date']['date_to'], company_id.id]
        cond = [options['date']['date_from'], options['date']['date_to'], company_id.id]
        self._cr.execute("""SELECT account_move_line_account_tax_rel.account_move_line_id
                FROM account_move_line_account_tax_rel
                INNER JOIN account_tax 
                ON account_move_line_account_tax_rel.account_tax_id = account_tax.id
                WHERE account_tax.id = %s""",(tax_id.id,))
        amls = self._cr.dictfetchall()
        lista = []
        for aml in amls:
            lista.append(aml.get('account_move_line_id'))

        inv_cond = """"""
        if options.get('invoice_number'):
            inv_cond = """and am.name ilike %s """
            cond.append('%%%s%%' % options.get('invoice_number'))

        tuppartnerids = tuple(options.get('partner_ids'))
        partner_cond = """"""
        if options.get('partner_ids'):
            partner_cond = """and aml.partner_id in """ + str(tuppartnerids) 
            if len(options.get('partner_ids')) == 1 :
                partner_cond = """and aml.partner_id =""" + str(options.get('partner_ids')[0])

        vatp_cond = """"""
        if options.get('vat_number'):
            vatp_cond = """and rp.vat ilike %s """
            cond.append('%%%s%%' % options.get('vat_number'))
        
        tupamlid = tuple(lista)
        aml_cond = """"""
        if lista:
            aml_cond = """and aml.id in """ + str(tupamlid) 
            if len(lista) == 1 :
                aml_cond = """and aml.id = """ + str(lista[0]) 
                
        self._cr.execute("""
            SELECT aml.id as id, am.company_id, am.name, aml.account_id, rp.name as partner_name, rp.vat as partner_vat, 
                aml.partner_id, aml.date, aml.product_id, ai.vat_invoice_no as vat_invoice_number, 
                CASE WHEN ai.type in ('out_refund', 'in_refund')
                then -aml.countered_amt
                else aml.countered_amt end as tax_amount
            FROM account_move_line aml
            JOIN account_move am on aml.move_id = am.id
            JOIN account_account aa on aa.id = aml.account_id
            LEFT JOIN account_invoice ai on ai.id = aml.invoice_id
            LEFT JOIN product_product pp on pp.id = aml.product_id
            LEFT JOIN res_partner rp on rp.id = aml.partner_id
            WHERE (aml.date_accounting >= %s) and
                (aml.date_accounting <= %s) and aml.company_id = %s """+ aml_cond +""" and am.state = 'posted'  """+ partner_cond + inv_cond + vatp_cond +"""
            ORDER BY aml.date, am.name
        """, tuple(cond))
        vat_report_results = self._cr.dictfetchall()
        return vat_report_results
    
    def get_all_total(self, options, line_id, type='purchase'):
        tax_ids = self.env['account.tax'].sudo().search([('type_tax_use','=',type)])
        sum_base = 0
        sum_taxed = 0
        context = self.env.context
        for tax_id in tax_ids:
            
            results = self._get_aml_by_tax(options, tax_id)
            for am in results:
                taxed = 0
                if tax_id.amount_type == 'percent':
                    taxed = am.get('tax_amount') * (tax_id.amount/100)
                elif tax_id.amount_type == 'fixed':
                    taxed = tax_id.amount
                sum_base+=am.get('tax_amount')
                sum_taxed+=taxed

        return {
            'global_base':sum_base,
            'global_taxed':sum_taxed,
        }

    def _group_by_tax_id(self, options, line_id, type='purchase'):
        taxes = {}
        date_from = options['date']['date_from']
        tax_ids = self.env['account.tax'].sudo().search([('type_tax_use','=',type)])
        if line_id and not self.env.context.get('print_mode'):
            tax_ids = self.env['account.tax'].sudo().search([('id','=',line_id)])
        
        context = self.env.context
        base_domain = [('date', '<=', context['date_to']), ('company_id', 'in', context['company_ids'])]
        base_domain.append(('date', '>=', date_from))
        for tax_id in tax_ids:
            results = self._get_aml_by_tax(options, tax_id)
            taxes[tax_id] = {}
            domain = list(base_domain)  # copying the base domain
            domain.append(('id', '=', self._get_amlids_by_tax(tax_id)))
            taxes[tax_id]['total_lines'] = len(results)
            taxes[tax_id]['lines'] = results

        return taxes

    @api.model
    def _get_lines(self, options, line_id=None):
        offset = int(options.get('lines_offset', 0))
        lines = []
        context = self.env.context
        company_id = self.env.user.company_id
        used_currency = company_id.currency_id
        dt_from = options['date'].get('date_from')
        line_id = line_id and int(line_id.split('_')[1]) or None
        aml_lines = []
        # Aml go back to the beginning of the user chosen range but the amount on the account line should go back to either the beginning of the fy or the beginning of times depending on the account
        grouped_taxes = self.with_context(date_from_aml=dt_from, date_from=dt_from or None)._group_by_tax_id(options, line_id, 'sale')
        unfold_all = context.get('print_mode') or len(options.get('unfolded_lines')) == 0
        
        total = self.with_context(date_from_aml=dt_from, date_from=dt_from or None).get_all_total(options, None, 'sale')
        
        global_base = 0
        global_taxed = 0

        for tax in grouped_taxes:
            sum_base = 0
            sum_taxed = 0
            display_name = tax.name
            if offset == 0:
                lines.append({
                    'id': 'tax_%s' % (tax.id,),
                    'name': len(display_name) > 40 and not context.get('print_mode') and display_name[:40]+'...' or display_name,
                    'title_hover': display_name,
                    'columns': [{'name': v} for v in ['','','','', '', '', '','']],
                    'level': 2,
                    'unfoldable': True,
                    'unfolded': 'tax_%s' % (tax.id,) in options.get('unfolded_lines') or unfold_all,
                    
                })
            if 'tax_%s' % (tax.id,) in options.get('unfolded_lines') or unfold_all:
                # initial_debit = grouped_accounts[account]['initial_bal']['debit']
                # initial_credit = grouped_accounts[account]['initial_bal']['credit']
                # initial_balance = grouped_accounts[account]['initial_bal']['balance']
                # initial_currency = '' if not account.currency_id else self.with_context(no_format=False).format_value(grouped_accounts[account]['initial_bal']['amount_currency'], currency=account.currency_id)

                domain_lines = []
                # if offset == 0:
                #     domain_lines.append({
                #         'id': 'initial_%s' % (tax.id,),
                #         'class': 'o_account_reports_initial_balance',
                #         'name': _('Initial Balance'),
                #         'parent_id': 'tax_%s' % (tax.id,),
                #         # 'columns': [{'name': v} for v in ['', '', '', initial_currency, self.format_value(initial_debit), self.format_value(initial_credit), self.format_value(initial_balance)]],
                #     })
                #     # progress = initial_balance
                # else:
                #     print('')
                #     # for load more:
                #     # progress = float(options.get('lines_progress', initial_balance))

                amls = grouped_taxes[tax]['lines']

                remaining_lines = 0
                if not context.get('print_mode'):
                    remaining_lines = grouped_taxes[tax]['total_lines'] - offset - len(amls)

                seq = 1
                for am in amls:
                    line = self.env['account.move.line'].browse(am.get('id'))
                    name = line.name and line.name or ''
                    if line.ref:
                        name = name and name + ' - ' + line.ref or line.ref
                    name_title = name
                    # Don't split the name when printing
                    if len(name) > 35 and not self.env.context.get('no_format') and not self.env.context.get('print_mode'):
                        name = name[:32] + "..."
                    invoice_vat = line.invoice_id.vat_invoice_no
                    invoice_date = line.invoice_id.date_invoice
                    partner_name = line.partner_id.name
                    partner_vat = line.partner_id.vat
                    partner_name_title = partner_name
                    taxed = 0
                    if tax.amount_type == 'percent':
                        taxed = am.get('tax_amount') * (tax.amount/100)
                    elif tax.amount_type == 'fixed':
                        taxed = tax.amount
                    sum_base+=am.get('tax_amount')
                    sum_taxed+=taxed
                    if partner_name and len(partner_name) > 35  and not self.env.context.get('no_format') and not self.env.context.get('print_mode'):
                        partner_name = partner_name[:32] + "..."
                    caret_type = 'account.move'
                    # if line.invoice_id:
                    #     caret_type = 'account.invoice.in' if line.invoice_id.type in ('in_refund', 'in_invoice') else 'account.invoice.out'
                    if line.move_id:
                        caret_type = 'account.move'
                    elif line.payment_id:
                        caret_type = 'account.payment'
                    columns = [{'name': v} for v in [invoice_vat, invoice_date, partner_name, partner_vat, line.product_id.name, self.format_value(am.get('tax_amount')), self.format_value(taxed), line.invoice_id.note ]]
                    columns[1]['class'] = 'whitespace_print'
                    columns[2]['class'] = 'whitespace_print'
                    columns[1]['title'] = name_title
                    columns[2]['title'] = partner_name_title
                    line_value = {
                        'id': line.id,
                        'caret_options': caret_type,
                        'class': 'top-vertical-align',
                        'parent_id': 'tax_%s' % (tax.id,),
                        'name': line.move_id.name if line.move_id.name else '/',
                        'columns': columns,
                        'level': 4,
                    }
                    aml_lines.append(line.id)
                    domain_lines.append(line_value)
                    seq+=1

                # load more
                if remaining_lines > 0:
                    domain_lines.append({
                        'id': 'loadmore_%s' % account.id,
                        # if MAX_LINES is None, there will be no remaining lines
                        # so this should not cause a problem
                        'offset': offset + self.MAX_LINES,
                        'progress': progress,
                        'class': 'o_account_reports_load_more text-center',
                        'parent_id': 'tax_%s' % (tax.id,),
                        'name': _('Load more... (%s remaining)') % remaining_lines,
                        'colspan': 7,
                        'columns': [{}],
                    })
                # don't add total line for `load more`
                if offset == 0:
                    domain_lines.append({
                        'id': 'total_' + str(tax.id),
                        'class': 'o_account_reports_domain_total',
                        'parent_id': 'tax_%s' % (tax.id,),
                        'name': _('Tổng '),
                        'columns': [{'name': v} for v in ['', '', '', '', '', self.format_value(sum_base), self.format_value(sum_taxed), '']],
                    })

                lines += domain_lines

            global_base+=sum_base
            global_taxed+=sum_taxed
        if not line_id:
            lines.append({
                    'id': 'total_global',
                    'name': _('Tổng số toàn cầu'),
                    'title_hover': _('Tổng số toàn cầu'),
                    'columns': [{'name': v} for v in ['','','','', '', self.format_value(total.get('global_base')), self.format_value(total.get('global_taxed')),'']],
                    'level': 2,
                })
        return lines
    
    # for sales
    def get_xlsx(self, options, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(self._get_report_name()[:31])

        date_default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'num_format': 'yyyy-mm-dd', 'border': 1})
        date_default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': 'yyyy-mm-dd', 'border': 1})
        default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'border': 1})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'border': 1})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'border': 1, 'align': 'center'})
        super_col_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'align': 'center', 'border': 1})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'border': 1, 'font_color': '#666666'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'border': 1, 'font_color': '#666666'})
        level_2_col1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1, 'border': 1})
        level_2_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'border': 1})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'border': 1})
        level_3_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'border': 1})
        level_3_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1, 'border': 1})
        level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'border': 1})
        
        header_right_bold = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'align': 'center', 'bold': True, 'font_color': 'black'})
        header_right_normal = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'align': 'center', 'font_color': 'black'})
        header_right_bottom = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'align': 'right', 'font_color': 'black'})
        
        header_left_bold = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'align': 'left', 'bold': True, 'font_color': 'black'})
        header_left_normal = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'align': 'left', 'font_color': 'black'})
        
        footer_left_bold = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'align': 'left', 'bold': True, 'font_color': 'black'})
        footer_right_center = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'align': 'center', 'font_color': 'black'})
        footer_right_center_blod = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'align': 'center', 'bold': True, 'font_color': 'black'})

        #Set the first column width to 50
        sheet.set_column(0, 0, 27)
        sheet.set_column('B:B', 17)
        sheet.set_column('C:F', 17)
        sheet.set_column('G:G', 20)
        sheet.set_column('H:H', 13)
        sheet.set_column('I:I', 55)

        super_columns = self._get_super_columns(options)
        y_offset = 12
        
        # Todo in master: Try to put this logic elsewhere
        x = super_columns.get('x_offset', 0)
        for super_col in super_columns.get('columns', []):
            cell_content = super_col.get('string', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
            x_merge = 0
            if x_merge and x_merge > 1:
                sheet.merge_range(0, x, 0, x + (x_merge - 1), cell_content, super_col_style)
                x += x_merge
            else:
                sheet.write(0, x, cell_content, super_col_style)
                x += 1
        for row in self.get_header(options):
            x = 0
            for column in row:
                colspan = 1
                header_label = column.get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
                if colspan == 1:
                    sheet.write(y_offset, x, header_label, title_style)
                else:
                    sheet.merge_range(y_offset, x, y_offset, x + colspan - 1, header_label, title_style)
                x += colspan
            y_offset += 1
        ctx = self._set_context(options)
        ctx.update({'no_format':True, 'print_mode':True, 'prefetch_fields': False})
        # deactivating the prefetching saves ~35% on get_lines running time
        lines = self.with_context(ctx)._get_lines(options)
        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines)
        sheet.hide_gridlines(2)
        sheet.write('I2', 'Mẫu số: 01-1/GTGT', header_right_bold)
        sheet.write('I3', '(Ban hành kèm theo Thông tư số 156/2013/TT-BTC', header_right_normal)
        sheet.write('I4', 'ngày 06/11/2013 của Bộ Tài chính)', header_right_normal)
        sheet.write('A3', 'BẢNG KÊ HOÁ ĐƠN, CHỨNG TỪ HÀNG HOÁ, DỊCH VỤ BÁN RA', header_left_bold)
        sheet.write('A4', '(Kèm theo tờ khai thuế GTGT theo mẫu số 01/GTGT)', header_left_normal)
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        month_date_to = int(date_to.split('-')[1])
        if month_date_to <= 3:
            quarter = "1"
        elif month_date_to >= 4 and month_date_to <= 6:
            quarter = "2"
        elif month_date_to >= 7 and month_date_to <= 9:
            quarter = "3"
        else:
            quarter = "4"

        sheet.write('A5', 'Kỳ tính thuế: Tháng '+date_from.split('-')[1]+' năm '+date_from.split('-')[0]+' / Quý '+quarter+' Năm '+date_to.split('-')[0], header_left_normal)
        sheet.write('A7', 'Người nộp thuế: ' + self.env.user.company_id.name, header_left_normal)
        sheet.write('A8', 'Mã số thuế: '+ (options['vat_number'] or ''), header_left_normal)
        sheet.write('A9', 'Tên đại lý thuế (nếu có):', header_left_normal)
        sheet.write('A10', 'Mã số thuế: ', header_left_normal)
        sheet.write('I12', 'Đơn vị tiền: đồng Việt Nam', header_right_bottom)

        amount_without_tax = 0
        amount_with_tax = 0
        taxes = 0
        
        #write all data rows
        for y in range(0, len(lines)):
            level = lines[y].get('level')
            if lines[y].get('caret_options'):
                style = level_3_style
                col1_style = level_3_col1_style
            elif level == 0:
                y_offset += 1
                style = level_0_style
                col1_style = style
            elif level == 1:
                style = level_1_style
                col1_style = style
            elif level == 2:
                style = level_2_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_2_col1_total_style or level_2_col1_style
            elif level == 3:
                style = level_3_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_3_col1_total_style or level_3_col1_style
            else:
                style = default_style
                col1_style = default_col1_style

            #write the first column, with a specific style to manage the indentation
            cell_type, cell_value = self._get_cell_type_value(lines[y])
            if cell_type == 'date':
                sheet.write_datetime(y + y_offset, 0, cell_value, date_default_col1_style)
            else:
                sheet.write(y + y_offset, 0, cell_value, col1_style)
            
            if lines[y].get('id') == 'total_global':
                amount_without_tax = lines[y]['columns'][5].get('name')
                taxes = lines[y]['columns'][6].get('name')
                amount_with_tax = amount_without_tax + taxes

            # write all the remaining cells
            for x in range(1, len(lines[y]['columns']) + 1):
                cell_type, cell_value = self._get_cell_type_value(lines[y]['columns'][x - 1])
                if cell_type == 'date':
                    sheet.write_datetime(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, date_default_style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, style)

        y += y_offset+2
        sheet.write(y, 0, 'Tổng doanh thu hàng hóa, dịch vụ bán ra : '+str(amount_without_tax), header_left_normal)
        sheet.write(y+1, 0, 'Tổng doanh thu hàng hoá, dịch vụ bán ra chịu thuế GTGT : '+str(amount_with_tax), header_left_normal)
        sheet.write(y+2, 0, 'Tổng thuế GTGT của hàng hóa, dịch vụ bán ra : '+str(taxes), header_left_normal)

        sheet.write(y+4, 0, 'Tôi cam đoan số liệu khai trên là đúng và chịu trách nhiệm trước pháp luật về những số liệu đã khai.', header_left_normal)

        sheet.write(y+6, 0, 'NHÂN VIÊN ĐẠI LÝ THUẾ', footer_left_bold)
        sheet.write(y+7, 0, 'Họ và tên: _________________', header_left_normal)
        sheet.write(y+8, 0, 'Chứng chỉ hành nghề số: _________________', header_left_normal)

        sheet.write(y+5, 8, '_____________ , ngày ___________ tháng ___________ năm ___________', footer_right_center)
        sheet.write(y+6, 8, 'NGƯỜI NỘP THUẾ hoặc', footer_right_center_blod)
        sheet.write(y+7, 8, 'ĐẠI DIỆN HỢP PHÁP CỦA NGƯỜI NỘP THUẾ', footer_right_center_blod)
        sheet.write(y+8, 8, 'Ký tên, đóng dấu (ghi rõ họ tên và chức vụ)', footer_right_center)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
