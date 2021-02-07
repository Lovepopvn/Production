# -*- coding: utf-8 -*-

import logging
import base64
import io
try:
	from odoo.tools.misc import xlsxwriter
except ImportError:
	import xlsxwriter

from io import StringIO, BytesIO
from datetime import datetime, timedelta
from odoo.tools.misc import formatLang, format_date as odoo_format_date, get_lang

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

class WizardGenerateJournalLedger(models.TransientModel):
	_name = 'wizard.generate.journal.ledger'
	_description = 'Wizard Generate Journal Ledger'


	account_ids = fields.Many2many('account.account', string='G/L Account(s)',required=True)
	start_date = fields.Date(string='Start Date',required=True, default=lambda self:self._default_start_date())
	end_date = fields.Date(string='End Date',required=True, default=lambda self:self._default_end_date())
	name = fields.Char(string="Filename", readonly=True)
	data_file = fields.Binary(string="File", readonly=True)
	with_currency = fields.Boolean(string='With Currency',default=False)

	def _default_start_date(self):
		return fields.Date.today().strftime('%Y-01-01')

	def _default_end_date(self):
		return fields.Date.today().strftime('%Y-12-31')



	def button_generate_excel(self):
		self = self.with_context(lang='vi_VN')
		output = io.BytesIO()
		workbook = xlsxwriter.Workbook(output)
		
		# format
		header_text = workbook.add_format({'text_wrap':True})
		header_text.set_align('center')
		header_text.set_align('vcenter')

		header_text_bold = workbook.add_format({'text_wrap':True,'bold':True})
		header_text_bold.set_align('center')
		header_text_bold.set_align('vcenter')


		border_text = workbook.add_format({'text_wrap':True})
		border_text.set_align('center')
		border_text.set_align('vcenter')
		border_text.set_border()
		
		header_table = workbook.add_format({'bold':True,'valign':'vcenter','align':'center','text_wrap':True})
		header_table.set_border()
		
		
		
		border_right_text = workbook.add_format({'text_wrap':True})
		border_right_text.set_align('right')
		border_right_text.set_align('vcenter')
		border_right_text.set_border()

		border_currency_right_text = workbook.add_format()
		border_currency_right_text.set_align('right')
		border_currency_right_text.set_align('vcenter')
		border_currency_right_text.set_border()
		border_currency_right_text.set_num_format('#,##0.00')

		border_left_text = workbook.add_format()
		border_left_text.set_align('left')
		border_left_text.set_align('vcenter')
		border_left_text.set_border()

		#Header
		header_report_bold = workbook.add_format({
			'bold':True, 'valign':'vcenter', 'align':'center',
			'text_wrap':True
			})




		# set body
		row = 5
		footer_row = 0
		
		for acc in self.account_ids:
			sheet = workbook.add_worksheet(str(acc.code))
			company_id = self.env.user.company_id
			if self.with_currency:
				total_init_debit_cur = 0
				total_init_credit_cur = 0
				total_init_cur = 0
				currency = ''
				curr_initial_balance = self.env['account.move.line.ctp'].search([('move_id.state','=','posted'), ('move_id.date','<',self.start_date), '|', ('dr_account_id','=',acc.id), ('cr_account_id','=',acc.id)]).sorted(lambda r:(r.move_id.date,r.move_id.name))
				for ctp in curr_initial_balance:
					if ctp.currency_id:
						currency = ctp.currency_id.name or ''
					amount_pos = 'debit'
					if ctp.dr_account_id.id == acc.id:
						amount_pos = 'debit'
					elif ctp.cr_account_id.id == acc.id:
						amount_pos = 'credit'
					if amount_pos=='debit':
						total_init_debit_cur += ctp.countered_amt_currency
					elif amount_pos == 'credit':
						total_init_credit_cur += ctp.countered_amt_currency
				total_init_cur = total_init_debit_cur - total_init_credit_cur
			sheet.set_column('A:I', 25)
			sheet.set_column('J:K', 30)

			sheet.merge_range('A1:B1',_("%s") % (company_id.name,))
			sheet.merge_range("A2:E2", _("%s, %s, %s, %s, %s") % (company_id.street or '', company_id.street2 or '', company_id.city or '', company_id.state_id.name or '', company_id.country_id.name or '',))

			sheet.set_row(row-1, 30)

			
			headmergecol = 'G'
			if self.with_currency:
				headmergecol = 'K'
			sheet.merge_range(_('A%s:%s%s') % (row,headmergecol,row),_("SỔ CHI TIẾT TÀI KHOẢN\n(Journal Ledger)"), header_report_bold)

			# sheet.set_row(row+1, 35)
			# sheet.merge_range(_('A%s:K%s') % (row+1,row+1),_("Tài khoản: %s - %s\nAccount: %s - %s") % (acc.code, acc.name, acc.code, acc.name, ), header_report_bold)
			sheet.merge_range(_('A%s:%s%s') % (row+1,headmergecol, row+1),_("Tài khoản: %s - %s") % (acc.code, acc.name, ), header_report_bold)
			sheet.merge_range(_('A%s:%s%s') % (row+2,headmergecol, row+2),_("Account: %s - %s") % (acc.code, acc.en_name, ), header_report_bold)
			sheet.merge_range(_('A%s:%s%s') % (row+3,headmergecol, row+3),_("Từ ngày %s đến ngày %s") % (odoo_format_date(self.env, self.start_date), odoo_format_date(self.env, self.end_date)), header_report_bold)
			sheet.merge_range(_('A%s:%s%s') % (row+4,headmergecol, row+4),_("From %s To %s") % (odoo_format_date(self.env, self.start_date), odoo_format_date(self.env, self.end_date)), header_report_bold)

			#Header Table
			sheet.set_row(row+6, 30)
			sheet.merge_range(_('A%s:B%s') % (row+7,row+7),_("Chứng từ\n(Document)"), header_table)
			sheet.merge_range(_('F%s:G%s') % (row+7,row+7),_("Số phát sinh\n(Amount incurred)"), header_table)
			if self.with_currency:
				sheet.merge_range(_('J%s:K%s') % (row+7,row+7),_("Số phát sinh ngoại tệ\n(Amount incurred in foregin currency)"), header_table)

			sheet.merge_range(_('C%s:C%s') % (row+7,row+8),_("Khách hàng\n(Partner)"), header_table)
			sheet.merge_range(_('D%s:D%s') % (row+7,row+8),_("Diễn giải\n(Description)"), header_table)
			sheet.merge_range(_('E%s:E%s') % (row+7,row+8),_("Tài khoản đối ứng\n(Counterpart)"), header_table)
			if self.with_currency:
				sheet.merge_range(_('H%s:H%s') % (row+7,row+8),_("Ngoại tệ\n(Currencies)"), header_table)
				sheet.merge_range(_('I%s:I%s') % (row+7,row+8),_("Tỷ giá\n(Exchange rate)"), header_table)

			sheet.set_row(row+7, 30)
			sheet.write(_('A%s') % (row+8),_("Ngày\n(Date)"), header_table)
			sheet.write(_('B%s') % (row+8),_("Số\n(Number)"), header_table)
			sheet.write(_('F%s') % (row+8),_("Nợ\n(Debit)"), header_table)
			sheet.write(_('G%s') % (row+8),_("Có\n(Credit)"), header_table)
			if self.with_currency:
				sheet.write(_('J%s') % (row+8),_("Nợ\n(Debit)"), header_table)
				sheet.write(_('K%s') % (row+8),_("Có\n(Credit)"), header_table)
			
			# move_line = self.env['account.move.line'].search([('move_id.state','=','posted'), ('account_id','=',acc.id), ('move_id.date','>=',self.start_date), ('move_id.date','<=',self.end_date)])
			# move_ids = move_line.filtered(lambda r: r.move_id.state == 'posted' and r.move_id.date >= self.start_date and r.move_id.date <= self.end_date).mapped('move_id')
			# counterpart_ids = self.env['account.move.line.ctp'].search([('move_id','in',move_ids.ids)])
			# counterpart_ids = move_line.mapped(lambda r:r.ctp_aml_ids.mapped('ctp_ids')).sorted(lambda r:(r.move_id.date,r.move_id.name))
			counterpart_ids = self.env['account.move.line.ctp'].search([('move_id.state','=','posted'), ('move_id.date','>=',self.start_date), ('move_id.date','<=',self.end_date), '|', ('dr_account_id','=',acc.id), ('cr_account_id','=',acc.id)]).sorted(lambda r:(r.move_id.date,r.move_id.name))
			gl_obj = self.env['account.general.ledger']
			line_id = 'account_%d' % (acc.id,)
			options = {
				'unfolded_lines': [line_id], 
				'date': {
					'string': 'Custom', 
					'period_type': 'month', 
					'mode': 'range', 
					'date_from': self.start_date, 
					'date_to': self.end_date, 
					'filter': ''}, 
					'all_entries': False, 
					'analytic': True, 
					'journals': 
					[{'id': 'divider', 'name': self.create_uid.company_id.name}, {'id': 7, 'name': 'Bank', 'code': 'BNK1', 'type': 'bank', 'selected': False}, {'id': 6, 'name': 'Cash', 'code': 'CSH1', 'type': 'cash', 'selected': False}, {'id': 5, 'name': 'Cash Basis Taxes', 'code': 'CABA', 'type': 'general', 'selected': False}, {'id': 8, 'name': 'Closing Balance', 'code': 'CLOSE', 'type': 'general', 'selected': False}, {'id': 1, 'name': 'Customer Invoices', 'code': 'INV', 'type': 'sale', 'selected': False}, {'id': 4, 'name': 'Exchange Difference', 'code': 'EXCH', 'type': 'general', 'selected': False}, {'id': 3, 'name': 'Miscellaneous Operations', 'code': 'MISC', 'type': 'general', 'selected': False}, {'id': 2, 'name': 'Vendor Bills', 'code': 'BILL', 'type': 'purchase', 'selected': False}], 'unfold_all': False, 'unposted_in_period': False}

			no_result = False
			try:
				gl = gl_obj.with_context(no_format=True, date_from=self.start_date, date_to=self.end_date)._get_general_ledger_lines(options, line_id=line_id)
			except Exception as e:
				no_result = True
				
			if no_result:
				colend = 'G'
				if self.with_currency:
					colend = 'K'
				sheet.merge_range(_('A%s:%s%s') % (row+9,colend, row+9,),_("No Result"), border_text)
				row_line = row+8
				# row = row + row_line + 3
				footer_row = row_line + 5
				if self.with_currency:
					sheet.write(_('A%s') % (footer_row),_("NGƯỜI GHI SỔ"), header_text_bold)
					sheet.write(_('A%s') % (footer_row+1),_("(Ký, họ tên)"), header_text)
					sheet.write(_('F%s') % (footer_row),_("KẾ TOÁN TRƯỞNG"), header_text_bold)
					sheet.write(_('F%s') % (footer_row+1),_("(Ký, họ tên)"), header_text)
					sheet.write(_('K%s') % (footer_row-1),_("Ngày........tháng........năm................"), header_text)
					sheet.write(_('K%s') % (footer_row),_("GIÁM ĐỐC"), header_text_bold)
					sheet.write(_('K%s') % (footer_row+1),_("(Ký, họ tên)"), header_text)
				elif not self.with_currency:
					sheet.write(_('A%s') % (footer_row),_("NGƯỜI GHI SỔ"), header_text)
					sheet.write(_('A%s') % (footer_row+1),_("(Ký, họ tên)"), header_text)
					sheet.write(_('D%s') % (footer_row),_("KẾ TOÁN TRƯỞNG"), header_text)
					sheet.write(_('D%s') % (footer_row+1),_("(Ký, họ tên)"), header_text)
					sheet.write(_('G%s') % (footer_row-1),_("Ngày........tháng........năm................"), header_text)
					sheet.write(_('G%s') % (footer_row),_("GIÁM ĐỐC"), header_text)
					sheet.write(_('G%s') % (footer_row+1),_("(Ký, họ tên)"), header_text)
				# end 
				continue
			sheet.set_row(row+8, 30)
			# opening_balance = float(gl[1].get('columns')[3].get('name').split(' ')[0].replace(',','').replace('.',''))
			opening_balance = 0.0
			try:
				if acc.user_type_id.include_initial_balance:
					opening_balance = float(gl[1].get('columns')[3].get('name'))
			except:
				opening_balance = 0.0
			
			credit_opening_balance = 0.0
			debit_opening_balance = abs(opening_balance)
			if opening_balance<0.0:
				credit_opening_balance = abs(opening_balance)
				debit_opening_balance = 0.0
			sheet.merge_range(_('A%s:E%s') % (row+9,row+9),_("Số dư đầu kỳ\n(Openning balance)"), border_text)
			sheet.write_formula(_('F%s') % (row+9), _("=ABS(%s)") % debit_opening_balance, border_currency_right_text)
			sheet.write_formula(_('G%s') % (row+9), _("=ABS(%s)") % credit_opening_balance, border_currency_right_text)
			if self.with_currency:
				sheet.write(_('H%s') % (row+9),_("%s")%(currency,), border_right_text)
				sheet.write(_('I%s') % (row+9),_("%s")%('',), border_right_text)
				# sheet.merge_range(_('H%s:K%s') % (row+9,row+9),'', border_text)			
				if total_init_cur>0:
					sheet.write(_('J%s') % (row+9), total_init_cur,border_currency_right_text)
					sheet.write(_('K%s') % (row+9), 0,border_currency_right_text)
				else:
					sheet.write(_('J%s') % (row+9), 0,border_currency_right_text)
					sheet.write(_('K%s') % (row+9), abs(total_init_cur),border_currency_right_text)
			row_line = row+10
			total_debit = 0.0
			total_credit = 0.0
			total_debit_cur = 0.0
			total_credit_cur = 0.0
			for ctp in counterpart_ids:
				sheet.write(_('A%s') % (row_line),_("%s")%(odoo_format_date(self.env, ctp.move_id.date) or '',), border_right_text)
				sheet.write(_('B%s') % (row_line),_("%s")%(ctp.move_id.name or '',), border_left_text)
				sheet.write(_('C%s') % (row_line),_("%s")%(ctp.cr_aml_id.partner_id.name or '' if ctp.dr_account_id.id == acc.id else ctp.dr_aml_id.partner_id.name or '',), border_text)
				sheet.write(_('D%s') % (row_line),_("%s")%(ctp.move_id.ref or '',), border_text)
				sheet.write(_('E%s') % (row_line),_("%s")%(ctp.cr_account_id.code or '' if ctp.dr_account_id.id == acc.id else ctp.dr_account_id.code or '',), border_right_text)

				amount_pos = 'debit'
				if ctp.dr_account_id.id == acc.id:
					amount_pos = 'debit'
				elif ctp.cr_account_id.id == acc.id:
					amount_pos = 'credit'

				debit_val = ctp.countered_amt if ctp.dr_account_id.id == acc.id else 0.00
				credit_val = ctp.countered_amt if ctp.cr_account_id.id == acc.id else 0.00

				sheet.write(_('F%s') % (row_line), debit_val,border_currency_right_text)
				sheet.write(_('G%s') % (row_line), credit_val,border_currency_right_text)
				total_debit = total_debit + float(debit_val)
				total_credit = total_credit + float(credit_val)
				if self.with_currency:
					sheet.write(_('H%s') % (row_line),_("%s")%(ctp.currency_id.name or '',), border_right_text)
					currency_rate = 0.0
					if ctp.currency_id.id:
						currency_rate = ctp.currency_id._get_rates(ctp.move_id.company_id,ctp.move_id.date.strftime('%Y-%m-%d')).get(ctp.currency_id.id)
						# currency_rate = 
						currency_rate = ctp.countered_amt_currency and (ctp.countered_amt / ctp.countered_amt_currency) or 0

					sheet.write(_('I%s') % (row_line), currency_rate, border_currency_right_text)
					if amount_pos=='debit':
						sheet.write(_('J%s') % (row_line), ctp.countered_amt_currency or 0.00,border_currency_right_text)
						sheet.write(_('K%s') % (row_line),0.00,border_currency_right_text)
						total_debit_cur += ctp.countered_amt_currency

					elif amount_pos == 'credit':
						
						sheet.write(_('J%s') % (row_line), 0.00,border_currency_right_text)
						sheet.write(_('K%s') % (row_line), ctp.countered_amt_currency or 0.00, border_currency_right_text)					
						total_credit_cur += ctp.countered_amt_currency

				row_line = row_line + 1

			sheet.set_row(row_line-1, 30) # index set_row() mulai dari 0
			sheet.set_row(row_line, 30)
			sheet.merge_range(_('A%s:E%s') % (row_line,row_line),_("Tổng số phát sinh trong kỳ\n(Total amount incurred in the period)"), header_table)
			sheet.write(_('F%s') % (row_line),total_debit or 0.00,border_currency_right_text)
			sheet.write(_('G%s') % (row_line),total_credit or 0.00,border_currency_right_text)

			closed_balance = (debit_opening_balance + total_debit) - (credit_opening_balance + total_credit)
			debit_cb = abs(closed_balance)
			credit_cb = 0.0
			if closed_balance<0.0:
				debit_cb = 0.0
				credit_cb = abs(closed_balance)

			sheet.merge_range(_('A%s:E%s') % (row_line+1,row_line+1),_("Số dư cuối kỳ\n(Closing balance)"), header_table)
			sheet.write_formula(_('F%s') % (row_line+1), _("=ABS(%s)") % debit_cb,border_currency_right_text)
			sheet.write_formula(_('G%s') % (row_line+1), _("=ABS(%s)") % credit_cb,border_currency_right_text)
			if self.with_currency:
				# sheet.merge_range(_('H%s:K%s') % (row_line+1,row_line+1),'', border_text)
				# sheet.merge_range(_('H%s:K%s') % (row_line,row_line),'', border_text)
				sheet.write(_('H%s') % (row_line), '',border_currency_right_text)
				sheet.write(_('I%s') % (row_line), '', border_currency_right_text)
				sheet.write(_('H%s') % (row_line+1), '',border_currency_right_text)
				sheet.write(_('I%s') % (row_line+1), '', border_currency_right_text)
				sheet.write(_('J%s') % (row_line), total_debit_cur,border_currency_right_text)
				sheet.write(_('K%s') % (row_line), total_credit_cur, border_currency_right_text)
				closing_balance = (total_init_debit_cur+total_debit_cur) - (total_init_credit_cur+total_credit_cur)
				if closing_balance > 0:
					sheet.write(_('J%s') % (row_line+1), closing_balance ,border_currency_right_text)
					sheet.write(_('K%s') % (row_line+1), 0, border_currency_right_text)
				else:
					sheet.write(_('J%s') % (row_line+1), 0 ,border_currency_right_text)
					sheet.write(_('K%s') % (row_line+1), abs(closing_balance), border_currency_right_text)


			# row = row + row_line + 3
			footer_row = row_line + 5

			if self.with_currency:
				sheet.write(_('A%s') % (footer_row),_("NGƯỜI GHI SỔ"), header_text_bold)
				sheet.write(_('A%s') % (footer_row+1),_("(Ký, họ tên)"), header_text)
				sheet.write(_('F%s') % (footer_row),_("KẾ TOÁN TRƯỞNG"), header_text_bold)
				sheet.write(_('F%s') % (footer_row+1),_("(Ký, họ tên)"), header_text)
				sheet.write(_('K%s') % (footer_row-1),_("Ngày........tháng........năm................"), header_text)
				sheet.write(_('K%s') % (footer_row),_("GIÁM ĐỐC"), header_text_bold)
				sheet.write(_('K%s') % (footer_row+1),_("(Ký, họ tên)"), header_text)
			elif not self.with_currency:
				sheet.write(_('A%s') % (footer_row),_("NGƯỜI GHI SỔ"), header_text_bold)
				sheet.write(_('A%s') % (footer_row+1),_("(Ký, họ tên)"), header_text)
				sheet.write(_('D%s') % (footer_row),_("KẾ TOÁN TRƯỞNG"), header_text_bold)
				sheet.write(_('D%s') % (footer_row+1),_("(Ký, họ tên)"), header_text)
				sheet.write(_('G%s') % (footer_row-1),_("Ngày........tháng........năm................"), header_text)
				sheet.write(_('G%s') % (footer_row),_("GIÁM ĐỐC"), header_text_bold)
				sheet.write(_('G%s') % (footer_row+1),_("(Ký, họ tên)"), header_text)

		workbook.close()
		out = base64.b64encode(output.getvalue())
		output.close()
		filename = ('journal_ledger_%s.xlsx')%(self.start_date)
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
			'url': '/web/content/%s/%s/data_file/%s' % (self._name, self.id, filename,),
		}
