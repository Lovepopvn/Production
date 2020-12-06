import io
import json

try:
	from odoo.tools.misc import xlsxwriter
except ImportError:
	# TODO saas-17: remove the try/except to directly import from misc
	import xlsxwriter
from lxml import etree,html
from io import StringIO, BytesIO
from dateutil.relativedelta import relativedelta

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, pycompat, config, date_utils
from odoo.tools.safe_eval import safe_eval

from odoo import api, fields, models, _
from datetime import date,datetime,timedelta
from calendar import monthrange
from odoo.tools.misc import format_date
from odoo.exceptions import UserError,MissingError
from odoo.http import request

from odoo.addons.account_reports.models.account_financial_report import FormulaLine
import logging
_logger = logging.getLogger(__name__)

class AccountFinancialHtmlReport(models.Model):
	_inherit = 'account.financial.html.report'
	
	def unlink(self):
		for report in self:
			default_parent_id = self.env['ir.model.data'].xmlid_to_res_id('account.menu_finance_reports')
			menu = self.env['ir.ui.menu'].search([('parent_id', '=', default_parent_id), ('name', '=', report.name)])
			if menu:
				menu.mapped('action').unlink()
				menu.unlink()
		return super(AccountFinancialHtmlReport, self).unlink()

	def _build_options(self, previous_options=None):
		# previous_options['unfold_all'] = True
		return super()._build_options(previous_options)

	def _validating_filter_today(self, options):
		today = fields.Datetime.now()
		date = options.get('date')
		if date:
			if today.strftime('%Y-%m-%d') != date.get('date_to'):
				filter_name = " ".join(date.get('filter').split('_'))
				raise UserError(_("%s Filter Only can be applied at Date %s") % (filter_name.title(), format_date(self.env,date.get('date_to')),))

	def _validating_filter_custom(self, options):
		date_from = datetime.strptime(options.get('date_from'), '%Y-%m-%d')
		m_range = monthrange(date_from.year, date_from.month)
		if options.get('date_to') != date_from.strftime('%Y-%m-')+ str(m_range[1]):
			raise UserError(_("Please Select Range in 1 Month!"))
		return True

	def _can_get_info(self, options):
		if self.id == self.env.ref('vn_vas_report.account_financial_report_pnl_b02').id:
			if options:
				dateoptions = options.get('date')
				if dateoptions:
					if dateoptions.get('filter') in ('this_month','this_quarter','this_year',):
						self._validating_filter_today(options)
					elif dateoptions.get('filter') in ('custom',):
						self._validating_filter_custom(dateoptions)

	# def _apply_date_filter(self, options):
	# 	res = super()._apply_date_filter(options)
	# 	return res

	def get_report_informations(self, options):
		def create_vals(period_vals):
			vals = {'string': period_vals['string']}
			if self.has_single_date_filter(options):
				vals['date'] = (period_vals['date_to'] or period_vals['date_from']).strftime(DEFAULT_SERVER_DATE_FORMAT)
			else:
				vals['date_from'] = period_vals['date_from'].strftime(DEFAULT_SERVER_DATE_FORMAT)
				vals['date_to'] = period_vals['date_to'].strftime(DEFAULT_SERVER_DATE_FORMAT)
			return vals

		if self.id in [self.env.ref('vn_vas_report.account_financial_report_b01').id, self.env.ref('vn_vas_report.account_financial_report_pnl_b02').id]:

			bs_report = self.env.ref('vn_vas_report.account_financial_report_b01')
			pnl_report = self.env.ref('vn_vas_report.account_financial_report_pnl_b02')

			if self.id == self.env.ref('vn_vas_report.account_financial_html_report_action_%s' % (bs_report.id,)).id:
				default_filter = 'today'
			elif self.id == self.env.ref('vn_vas_report.account_financial_html_report_action_%s' % (pnl_report.id,)).id:
				default_filter = 'last_month'
			else:
				default_filter = 'this_year'

			if not options:
				options = {'date':{'filter':default_filter}}
			elif not options.get('date'):
				options['date'] = {"filter":default_filter}
			elif options.get('date') and not options['date'].get('filter'):
				options['date'].update({'filter':default_filter})

			comparison = options.get('comparison')
			if comparison and comparison.get('number_period') in [1,0] and comparison.get('filter') != 'no_comparison':
				comparison.update({'filter':'previous_period', 'number_period':1, "string":"Previous Period",})
				options.update({'comparison':comparison})
			else:
				if not comparison:
					options.update({
						"comparison":{
							'filter':'previous_period',
							'number_period':1,
							"string":"Previous Period",
							"periods":[],
							"date_from":"",
							"date_to":""
						},

					})
			res = super().get_report_informations(options)

			new_options = res.get('options')
			new_options.update({
				'hide_no_comparison':True,
			})

			# if comparison:
			# 	if comparison.get('filter') == 'no_comparison':
			# 		comparison.update({'filter':'previous_period'})
			# 	new_options.update({'comparison':comparison})

			return res
		else:
			return super().get_report_informations(options)

	def _apply_date_filter(self, options):

		def create_vals(period_vals):
			vals = {'string': period_vals['string']}
			if self.has_single_date_filter(options):
				vals['date'] = (period_vals['date_to'] or period_vals['date_from']).strftime(DEFAULT_SERVER_DATE_FORMAT)
			else:
				vals['date_from'] = period_vals['date_from'].strftime(DEFAULT_SERVER_DATE_FORMAT)
				vals['date_to'] = period_vals['date_to'].strftime(DEFAULT_SERVER_DATE_FORMAT)
			return vals


		res = super()._apply_date_filter(options)


		options['hide_no_comparison'] = True
		return res

	def _set_xlsx_pnl_header(self, options, workbook, sheet):
		sheet.write('A1',_("Reporting entity: %s") % (self.env.user.company_id.name,))
		sheet.write("A2", _("Address: %s") % (self.env.user.company_id.partner_id.contact_address,))
		sheet.write("A3", _("INCOME STATEMENT"))
		dd_filter = options.get('date')
		dd_filter_to = datetime.strptime(dd_filter.get('date_to'), '%Y-%m-%d')
		year = dd_filter_to.strftime('%Y')

		sheet.write("A4", _("Year %s") % year)

		sheet.write("E1","Mẫu số B 02 – DN")
		sheet.write("E2","(Ban hành theo Thông tư số 200/2014/TT-BTC\nNgày 22/12/2014 của Bộ Tài chính)")
		sheet.write("E3","Unit: VND")

		table_style = workbook.add_format({"border":1,"bold":1})

		# table header
		sheet.write("A6", _("Items"),table_style)
		sheet.write("B6", _("Code"),table_style)
		sheet.write("C6", _("Description"),table_style)
		opt_date = options.get('date')

		sheet.write("D6" , opt_date.get('string'),table_style)
		# sheet.write("E6", "Previous Period")
		comparison = options.get('comparison')
		periods = comparison.get('periods')
		col_x = 4
		for period in periods:
			sheet.write(5, col_x, period.get('string'),table_style)
			col_x += 1


		sheet.write("A7", "1",table_style)
		sheet.write("B7", "2",table_style)
		sheet.write("C7", "3",table_style)
		sheet.write("D7" , "4",table_style)
		head_count = 5
		col_x = 4
		for period in periods:
			sheet.write(6, col_x, str(head_count), table_style)
			head_count += 1
			col_x += 1
		pass

	def _get_xlsx_pnl_styles(self, options, workbook, sheet):
		date_default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'num_format': 'yyyy-mm-dd'})
		date_default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': 'yyyy-mm-dd'})
		default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
		default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})
		title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
		super_col_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'align': 'center'})
		level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666'})
		level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666'})
		level_2_col1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
		level_2_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
		level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
		level_3_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
		level_3_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
		level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})

		return date_default_col1_style,date_default_style,default_col1_style,default_style,title_style,super_col_style,level_0_style,level_1_style,level_2_col1_style,level_2_col1_total_style,level_2_style,level_3_col1_style,level_3_col1_total_style,level_3_style


	def _set_xlsx_pnl_body(self, options, workbook, sheet):
		ctx = self._set_context(options)
		ctx.update({'no_format':True, 'print_mode':True, 'prefetch_fields': False})
		# deactivating the prefetching saves ~35% on get_lines running time
		lines = self.with_context(ctx)._get_lines(options)

		date_default_col1_style, date_default_style, default_col1_style, default_style, title_style, super_col_style, level_0_style,level_1_style,level_2_col1_style,level_2_col1_total_style,level_2_style,level_3_col1_style,level_3_col1_total_style,level_3_style = self._get_xlsx_pnl_styles(options, workbook, sheet)
		sheet.set_column(0, 0, 70)

		sheet.set_column(1, 1, 10)

		sheet.set_column(2, 2, 30)

		sheet.set_column(3, 3, 20)

		sheet.set_column(4, 4, 20)
		if options.get('hierarchy'):
			lines = self._create_hierarchy(lines)

		tbody_style = workbook.add_format({"left":1,'right':1})
		tbody_style_number = workbook.add_format({"left":1,'right':1,'num_format':'#,##0.00'})
		top_border_style = workbook.add_format({"top":1})



		#write all data rows
		x = 1
		y_offset = 7
		for y in range(0, len(lines)):
			level = lines[y].get('level')

			#write the first column, with a specific style to manage the indentation
			cell_type, cell_value = self._get_cell_type_value(lines[y])
			if cell_type == 'date':
				sheet.write_datetime(y + y_offset, 0, _(cell_value), date_default_col1_style)
			else:
				sheet.write(y + y_offset, 0, _(cell_value), tbody_style_number)

			sheet.write(y + y_offset, 1, lines[y].get('code').replace('PNL_B02_',''), tbody_style)

			#write all the remaining cells
			for x in range(1, len(lines[y]['columns']) + 1):
				cell_type, cell_value = self._get_cell_type_value(lines[y]['columns'][x - 1])
				colspan = lines[y].get('colspan', 1)
				if cell_type == 'date':
					sheet.write_datetime(y + y_offset, x + colspan - 1, cell_value, tbody_style)
				else:
					colspan = lines[y].get('colspan', 2)
					sheet.write(y + y_offset, x + colspan, cell_value, tbody_style_number)

		y += y_offset+1

		sheet.write(y, 0, _("(*) Only applying at joint-stock companies"),top_border_style)
		for x in range(1,5):
			sheet.write(y,x,"",top_border_style)



		y += 3
		sheet.write(y, 0, _("Prepared by"))
		sheet.write(y, 1, _("Chief accountant"))
		sheet.write(y, 3, _("Director"))

	def _get_xlsx_pnl(self, options, response):
		self = self.with_context(lang='vi_VN')
		output = io.BytesIO()
		workbook = xlsxwriter.Workbook(output, {'in_memory': True})
		sheet = workbook.add_worksheet(self._get_report_name()[:31])

		# set header
		self._set_xlsx_pnl_header(options, workbook, sheet)

		# set body
		self._set_xlsx_pnl_body(options, workbook, sheet)

		workbook.close()
		output.seek(0)
		response.stream.write(output.read())
		output.close()

	# def print_pdf(self, options):
	# 	vn_report = self.env.ref('vn_vas_report.account_financial_report_pnl_b02')
	# 	if self.id not in vn_report.ids:
	# 		return super().print_pdf(options)

	# 	context = self._context.copy()
	# 	context.update({'lang':'vi_VN'})
	# 	return {
	# 		'type': 'ir_actions_account_report_download',
	# 		'data': {
	# 			'model': self.env.context.get('model'),
	# 			'options': json.dumps(options),
	# 			'output_format': 'pdf',
	# 			'financial_id': self.env.context.get('id'),
	# 			'context':context,
	# 		},
	# 		'context':context,

	# 	}

	# def is_custom_b0x_report(self):
	# 	vn_report = self.env.ref('vn_vas_report.account_financial_report_pnl_b02')
	# 	if self.id in vn_report.ids:
	# 		return True
	# 	return False

	@api.model
	def _update_vietnam_report_menu(self):
		parent = self.env.ref('l10n_vn.account_reports_vn_statements_menu')
		if parent:
			for child in parent.child_id:
				data = eval(child.action.context)
				if data.get('model') == 'account.financial.html.report':
					report = self.env[data.get('model')].browse(data.get('id'))
					if not report:
						child.unlink()

	def _pnl_b02_footer(self):
		html = [
			"<table>",
				"<tr>",
					"<td width=\"300px\">Prepared By</td>",
					"<td width=\"300px\">Chief Accountant</td>",
					"<td width=\"300px\">Director</td>",
				"</tr>",
			"</table>"
		]
		return "".join(html)

	def _get_footer_vn(self):
		return [
			['Người lập biểu', '(Ký, họ tên)'],
			['Kế toán trưởng', '(Ký, họ tên)'],
			['Giám đốc', '(Ký, họ tên, đóng dấu)'],
		]

	def _get_report_dict(self, options):
		bs_report = self.env.ref('vn_vas_report.account_financial_report_b01')
		icf_report = self.env.ref('vn_vas_report.account_financial_report_icf_b03')
		report = {'name': self._get_report_name(),
				  'company_name': self.env.user.company_id.name,
				  'company_name_vn': self._get_report_company_name_vn(),
				  'company_address_vn': self._get_report_company_address_vn(),
				  'report_footer': self._get_footer_vn(),
				  'is_print_mode': self._context.get('print_mode', False)}
		if self == bs_report:
			report.update({'date_report_vn': self._get_date_report_vn(options),
						   'bs_header_text1_vn': self._get_bs_header_text1_vn(),
						   'bs_header_text2_vn': self._get_bs_header_text2_vn(is_html=True),
						   'bs_header_text3_vn': self._get_bs_header_text3_vn(),
						   'bs_header_text4_vn': self._get_bs_header_text4_vn(),
						   'bs_header_text5_vn': self._get_bs_header_text5_vn(),
						   'report_type': 'bs'})
		elif self == icf_report:
			report.update({'date_report_vn': self._get_year_report_vn(options),
						   'icf_header_text1_vn': self._get_icf_header_text1_vn(),
						   'icf_header_text2_vn': self._get_icf_header_text2_vn(is_html=True),
						   'icf_header_text3_vn': self._get_icf_header_text3_vn(),
						   'icf_header_text4_vn': self._get_icf_header_text4_vn(),
						   'icf_header_text5_vn': self._get_icf_header_text5_vn(),
						   'report_type': 'icf'})

		return report

	
	def get_html(self, options, line_id=None, additional_context=None):
		self = self.with_context(debug=True) # only for debug
		self = self.with_context(lang='vi_VN')
		# only for bs b01 dn
		customized_reports = self.env.ref('vn_vas_report.account_financial_report_b01')
		if self.id in customized_reports.ids:
			self = self.with_context(selected_line_id=line_id)
		
		pl_report = self.env.ref('vn_vas_report.account_financial_report_pnl_b02')
		bs_report = self.env.ref('vn_vas_report.account_financial_report_b01')
		icf_report = self.env.ref('vn_vas_report.account_financial_report_icf_b03')
		
		if self == pl_report:
			''' return the html value of report, or html value of unfolded line
				* if line_id is set, the template used will be the line_template
				otherwise it uses the main_template. Reason is for efficiency, when unfolding a line in the report
				we don't want to reload all lines, just get the one we unfolded.
			'''
			
			# Check the security before updating the context to make sure the options are safe.
			self._check_report_security(options)

			# Prevent inconsistency between options and context.

			self = self.with_context(self._set_context(options))

			templates = self._get_templates()
			report_manager = self._get_report_manager(options)
			report = {'name': self._get_report_name(),
					  'summary': report_manager.summary,
					  'company_name': self.env.user.company_id.name,
					  'report_type': 'pnl'}
			lines = self._get_lines(options, line_id=line_id)

			if options.get('hierarchy'):
				lines = self._create_hierarchy(lines)

			footnotes_to_render = []
			if self.env.context.get('print_mode', False):
				# we are in print mode, so compute footnote number and include them in lines values, otherwise, let the js compute the number correctly as
				# we don't know all the visible lines.
				footnotes = dict([(str(f.line), f) for f in report_manager.footnotes_ids])
				number = 0
				for line in lines:
					f = footnotes.get(str(line.get('id')))
					if f:
						number += 1
						line['footnote'] = str(number)
						footnotes_to_render.append({'id': f.id, 'number': number, 'text': f.text})

			rcontext = {'report': report,
						'lines': {'columns_header': self.get_header(options), 'lines': lines},
						'options': options,
						'context': self.env.context,
						'model': self,
						}
			if additional_context and type(additional_context) == dict:
				rcontext.update(additional_context)
			if self.env.context.get('analytic_account_ids'):
				rcontext['options']['analytic_account_ids'] = [
					{'id': acc.id, 'name': acc.name} for acc in self.env.context['analytic_account_ids']
				]

			render_template = templates.get('main_template', 'account_reports.main_template')
			if line_id is not None:
				render_template = templates.get('line_template', 'account_reports.line_template')
			html = self.env['ir.ui.view'].render_template(
				render_template,
				values=dict(rcontext),
			)
			if self.env.context.get('print_mode', False):
				for k, v in self._replace_class().items():
					html = html.replace(k, v)
				# append footnote as well
				html = html.replace(b'<div class="js_account_report_footnotes"></div>',
									self.get_html_footnotes(footnotes_to_render))
				if self.env.ref('vn_vas_report.account_financial_report_pnl_b02').id == self.id:
					footer = self._pnl_b02_footer().encode()
					html += footer

			return html
		elif self in [bs_report, icf_report]:
			self._check_report_security(options)

			# Prevent inconsistency between options and context.
			self = self.with_context(self._set_context(options))

			templates = self._get_templates()
			report_manager = self._get_report_manager(options)
			report = self._get_report_dict(options)
			report['summary'] = report_manager.summary

			if self == bs_report and self._context.get('print_mode'):
				lines = self._get_b01_custom_lines(options, line_id=line_id)
			elif self == icf_report and self._context.get('print_mode'):
				lines = self._get_b03_custom_lines(options, line_id=line_id)
			else:
				lines = self._get_lines(options, line_id=line_id)

			if options.get('hierarchy'):
				lines = self._create_hierarchy(lines)

			footnotes_to_render = []
			if self.env.context.get('print_mode', False):
				# we are in print mode, so compute footnote number and include them in lines values, otherwise, let the js compute the number correctly as
				# we don't know all the visible lines.
				footnotes = dict([(str(f.line), f) for f in report_manager.footnotes_ids])
				number = 0
				for line in lines:
					f = footnotes.get(str(line.get('id')))
					if f:
						number += 1
						line['footnote'] = str(number)
						footnotes_to_render.append({'id': f.id, 'number': number, 'text': f.text})

			rcontext = {'report': report,
						'lines': {'columns_header': self.get_header(options), 'lines': lines},
						'options': options,
						'context': self.env.context,
						'model': self,
						}
			if additional_context and type(additional_context) == dict:
				rcontext.update(additional_context)
			if self.env.context.get('analytic_account_ids'):
				rcontext['options']['analytic_account_ids'] = [
					{'id': acc.id, 'name': acc.name} for acc in self.env.context['analytic_account_ids']
				]

			render_template = templates.get('main_template', 'account_reports.main_template')
			if line_id is not None:
				render_template = templates.get('line_template', 'account_reports.line_template')
			html = self.env['ir.ui.view'].render_template(
				render_template,
				values=dict(rcontext),
			)
			if self.env.context.get('print_mode', False):
				for k, v in self._replace_class().items():
					html = html.replace(k, v)
				# append footnote as well
				html = html.replace(b'<div class="js_account_report_footnotes"></div>',
									self.get_html_footnotes(footnotes_to_render))
			return html
		else:
			return super().get_html(options, line_id, additional_context)

	def _get_report_company_name_vn(self):
		company_id = self.env.user.company_id
		return 'Đơn vị báo cáo: %s' % (company_id.name,)

	def _get_report_company_address_vn(self):
		company_id = self.env.user.company_id

		street_list = []
		if company_id.street:
			street_list.append(company_id.street)
		if company_id.street2:
			street_list.append(company_id.street2)

		location_list = []
		if company_id.city:
			location_list.append(company_id.city)
		if company_id.state_id:
			location_list.append(company_id.state_id.name)
		if company_id.zip:
			location_list.append(company_id.zip)
		if company_id.country_id:
			location_list.append(company_id.country_id.name)
		location = ', '.join(location_list)

		street = ', '.join(street_list)
		return 'Địa chỉ: %s\n%s' % (street, location,)

	def _get_date_report_vn(self, options):
		date_to = fields.Date.from_string(options['date']['date_to'])
		date_to_fmt = date_to.strftime('%d %B %Y').split(' ')
		return 'Tại ngày %s tháng %s năm %s' % (date_to_fmt[0], date_to_fmt[1], date_to_fmt[2],)

	def _get_year_report_vn(self, options):
		date_to = fields.Date.from_string(options['date']['date_to'])
		date_to_fmt = date_to.strftime('%d %B %Y').split(' ')
		return 'Năm %s' % (date_to_fmt[2],)

	def _get_report_show_status(self, line_ids):
		""" To get report show status, based from field 'show' in account_financial_html_report_line """
		line_ids_str = ', '.join(line_ids)
		sql = """SELECT id, show FROM account_financial_html_report_line WHERE id IN (%s)""" % (line_ids_str,)
		self._cr.execute(sql)
		fetchall = self._cr.fetchall()

		result = {}
		for id, show in fetchall:
			result[str(id)] = show
		return result

	# ======================================= BALANCE SHEET XLSX REPORT =======================================
	def _get_bs_header_text1_vn(self):
		return 'Mẫu số B 01 – DN'

	def _get_bs_header_text2_vn(self, is_html=False):
		if is_html:
			return '(Ban hành theo Thông tư số 200/2014/TT-BTC Ngày 22/12/2014 của Bộ Tài chính)'
		return '(Ban hành theo Thông tư số 200/2014/TT-BTC\nNgày 22/12/2014 của Bộ Tài chính)'

	def _get_bs_header_text3_vn(self):
		return 'BẢNG CÂN ĐỐI KẾ TOÁN'

	def _get_bs_header_text4_vn(self):
		return '(Áp dụng cho doanh nghiệp đáp ứng giả định hoạt động liên tục)'

	def _get_bs_header_text5_vn(self):
		return 'Đơn vị tính: VND'

	def _set_b01_column(self, sheet):
		sheet.set_column('A:A', 40)
		sheet.set_column('B:B', 12)
		sheet.set_column('C:C', 12)
		sheet.set_column('D:D', 12)
		sheet.set_column('E:E', 12)

	def _set_b01_row(self, sheet):
		sheet.set_row(1, 30)
		sheet.set_row(7, 40)

	def _get_b01_header_format(self, workbook):
		normal = workbook.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'font_size': 10})
		merge_format = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter',
											'font_size': 10, 'text_wrap': True})
		normal_bold = workbook.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'bold': True, 'font_size': 10})
		normal_italic = workbook.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'italic': True,
											 'font_size': 10})
		normal_bold_italic = workbook.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'bold': True,
												  'italic': True, 'font_size': 10})

		return normal, merge_format, normal_bold, normal_italic, normal_bold_italic

	def set_xlsxb01_header(self, options, workbook, sheet):
		normal, merge_format, normal_bold, normal_italic, normal_bold_italic = self._get_b01_header_format(workbook)

		company_name_vn = self._get_report_company_name_vn()
		company_address_vn = self._get_report_company_address_vn()

		sheet.write(0, 0, company_name_vn, normal)
		# sheet.write(0, 1, company_name_en, normal)
		sheet.write(1, 0, company_address_vn, normal)
		# sheet.write(1, 1, company_address_en, normal)

		sheet.merge_range('C1:E1', self._get_bs_header_text1_vn(), merge_format)
		sheet.merge_range('C2:E2', self._get_bs_header_text2_vn(), merge_format)

		sheet.write(3, 0, self._get_bs_header_text3_vn(), normal_bold)
		# sheet.write(3, 0, 'BALANCE SHEET', normal_bold)

		date_report_vn = self._get_date_report_vn(options)
		# date_report_en = 'At %s %s %s' % (date_to_fmt[1], date_to_fmt[0], date_to_fmt[2],)
		sheet.write(4, 0, date_report_vn, normal_bold)
		# sheet.write(4, 1, date_report_en, normal_bold)

		sheet.write(5, 0, self._get_bs_header_text4_vn(), normal_bold_italic)
		sheet.write(6, 4, self._get_bs_header_text5_vn(), normal_italic)

	def _get_b01_body_format(self, workbook):
		header = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'bold': True,
									  'font_size': 10, 'border': 1})
		level0 = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'bold': True,
									  'font_size': 10, 'border': 1})
		level0_right = workbook.add_format({'font_name': 'Arial', 'align': 'right', 'valign': 'vcenter', 'bold': True,
											'font_size': 10, 'border': 1})
		level1 = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'bold': True,
									  'font_size': 10, 'left': 1, 'right': 1})
		level1_right = workbook.add_format({'font_name': 'Arial', 'align': 'right', 'valign': 'vcenter', 'bold': True,
											'font_size': 10, 'left': 1, 'right': 1})
		level2 = workbook.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'bold': True,
									  'font_size': 10, 'left': 1, 'right': 1})
		level2_right = workbook.add_format({'font_name': 'Arial', 'align': 'right', 'valign': 'vcenter', 'bold': True,
											'font_size': 10, 'left': 1, 'right': 1})
		level3 = workbook.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'font_size': 10, 'left': 1,
									  'right': 1})
		level3_center = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter',
											 'font_size': 10, 'left': 1, 'right': 1})
		level3_right = workbook.add_format({'font_name': 'Arial', 'align': 'right', 'valign': 'vcenter',
											'font_size': 10, 'left': 1, 'right': 1})
		return header, level0, level1, level2, level3, level3_center, level0_right, level1_right, level2_right, \
			   level3_right

	def _get_b01_custom_lines(self, options, line_id=None):
		ctx = self._set_context(options)
		lines = self.with_context(ctx)._get_lines(options, line_id=line_id)

		# line_ids = [str(line['id']) for line in lines]
		line_ids = []
		for line in lines:
			if type(line['id'])==int:
				line_ids.append(str(line['id']))
		line_codes = self._get_report_line_code(line_ids)

		result = []
		lvl0 = []  # contains report line level 0
		for line in lines:
			lvl = line['level']
			if str(line['id']) in line_codes:
				code = line_codes[str(line['id'])]['code']
				parent_id = line_codes[str(line['id'])]['parent_id']
			else:
				code = False
				parent_id = False

			line['code'] = code
			line['parent_id'] = parent_id

			if lvl == 0:
				lvl0.append(line)
			else:
				result.append(line)

		new_result = []
		last_lvl1 = None
		for idx, res in enumerate(result):
			lvl = res['level']
			if lvl == 1:
				if idx > 0:
					if result[idx - 1]['level'] == 3 and last_lvl1 and res['parent_id'] != last_lvl1['parent_id']:
						new_result.append(lvl0[0])
						del lvl0[0]
				last_lvl1 = res

			new_result.append(res)

		new_result.append(lvl0[0])
		del lvl0[0]

		return new_result

	def _get_report_line_code(self, line_ids):
		line_ids_str = ', '.join(line_ids)
		sql = """SELECT id, code, parent_id FROM account_financial_html_report_line WHERE id IN (%s)""" % (line_ids_str,)
		self._cr.execute(sql)
		fetchall = self._cr.fetchall()

		result = {}
		for id, code, parent_id in fetchall:
			result[str(id)] = {'code': code[2:], 'parent_id': parent_id}
		return result

	def set_xlsxb01_body(self, options, workbook, sheet):
		header, level0, level1, level2, level3, level3_center, level0_right, level1_right, level2_right, \
		level3_right = self._get_b01_body_format(workbook)

		sheet.write(7, 0, _('Asset'), header)
		sheet.write(7, 1, _('Code_B01'), header)
		sheet.write(7, 2, _('Description_B01'), header)
		sheet.write(7, 3, _('Closing Balance'), header)
		sheet.write(7, 4, _('Opening Balance'), header)

		for i in range(5):
			sheet.write(8, i, i + 1, header)

		lines = self._get_b01_custom_lines(options)

		lvl0_row = []

		idx_row = 9
		for line in lines:
			lvl = line['level']
			if lvl <= 1:
				sheet.write(idx_row, 0, '', level3)
				sheet.write(idx_row, 1, '', level3)
				sheet.write(idx_row, 3, '', level3)
				sheet.write(idx_row, 4, '', level3)
				idx_row += 1
				if lvl == 0:
					format_cell = level0
					format_code_cell = level0
					format_value = level0_right
				else:
					format_cell = level1
					format_code_cell = level1
					format_value = level1_right
			elif lvl == 2:
				format_cell = level2
				format_code_cell = level1
				format_value = level2_right
			else:
				format_cell = level3
				format_code_cell = level3_center
				format_value = level3_right

			columns = line['columns']
			closing = columns[0].get('no_format_name',0)

			opening = ''
			if len(columns) > 1:
				opening = columns[1].get('no_format_name',0)

			sheet.write(idx_row, 0, line['name'], format_cell)
			sheet.write(idx_row, 1, line['code'], format_code_cell)
			if lvl == 0:
				sheet.write(idx_row, 2, '', format_cell)
				lvl0_row.append(idx_row)
			
			format_value.set_num_format('#,##0.00 "₫"')
			sheet.write(idx_row, 3, closing, format_value)
			sheet.write(idx_row, 4, opening, format_value)
			idx_row += 1

			if lvl == 1:
				sheet.write(idx_row, 0, '', level3)
				sheet.write(idx_row, 1, '', level3)
				sheet.write(idx_row, 3, '', level3)
				sheet.write(idx_row, 4, '', level3)
				idx_row += 1

		for row in lvl0_row:
			sheet.set_row(row, 40)

		normal = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'font_size': 10})
		normal_bold = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'bold': True,
										   'font_size': 10})

		footer_vn = self._get_footer_vn()
		sheet.write(idx_row + 1, 1, footer_vn[0][0], normal_bold)
		sheet.write(idx_row + 1, 2, footer_vn[1][0], normal_bold)
		sheet.write(idx_row + 1, 3, footer_vn[2][0], normal_bold)
		sheet.write(idx_row + 4, 1, footer_vn[0][1], normal)
		sheet.write(idx_row + 4, 2, footer_vn[1][1], normal)
		sheet.write(idx_row + 4, 3, footer_vn[2][1], normal)

	def get_xlsxb01(self, options, response):
		output = io.BytesIO()
		workbook = xlsxwriter.Workbook(output, {'in_memory': True})
		sheet = workbook.add_worksheet(self._get_report_name()[:31])

		self._set_b01_column(sheet)
		self._set_b01_row(sheet)

		self.set_xlsxb01_header(options, workbook, sheet)
		self.set_xlsxb01_body(options, workbook, sheet)

		workbook.close()
		output.seek(0)
		response.stream.write(output.read())
		output.close()

	# ======================================= END OF BALANCE SHEET XLSX REPORT =======================================

	# ======================================= CASH FLOW (B03) XLSX REPORT =======================================
	def _get_icf_header_text1_vn(self):
		return 'Mẫu số B 03 – DN'

	def _get_icf_header_text2_vn(self, is_html=False):
		if is_html:
			return '(Ban hành theo Thông tư số 200/2014/TT-BTC Ngày 22/12/2014 của Bộ Tài chính)'
		return '(Ban hành theo Thông tư số 200/2014/TT-BTC\nNgày 22/12/2014 của Bộ Tài chính)'

	def _get_icf_header_text3_vn(self):
		return 'BÁO CÁO LƯU CHUYỂN TIỀN TỆ'

	def _get_icf_header_text4_vn(self):
		return '(Phương pháp gián tiếp) (*)'

	def _get_icf_header_text5_vn(self):
		return 'Đơn vị tính: VND'

	def _set_b03_column(self, sheet):
		sheet.set_column('A:A', 50)
		sheet.set_column('B:B', 12)
		sheet.set_column('C:C', 12)
		sheet.set_column('D:D', 15)
		sheet.set_column('E:E', 15)

	def _set_b03_row(self, sheet):
		sheet.set_row(1, 30)
		# sheet.set_row(7, 40)

	def _get_b03_header_format(self, workbook):
		normal = workbook.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'font_size': 10})
		merge_format = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter',
											'font_size': 10, 'text_wrap': True})
		normal_bold = workbook.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'bold': True, 'font_size': 10})
		normal_italic = workbook.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'italic': True,
											 'font_size': 10})
		normal_bold_italic = workbook.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'bold': True,
												  'italic': True, 'font_size': 10})

		return normal, merge_format, normal_bold, normal_italic, normal_bold_italic

	def set_xlsxb03_header(self, options, workbook, sheet):
		normal, merge_format, normal_bold, normal_italic, normal_bold_italic = self._get_b03_header_format(workbook)

		company_name_vn = self._get_report_company_name_vn()
		company_address_vn = self._get_report_company_address_vn()

		sheet.write(0, 0, company_name_vn, normal)
		sheet.write(1, 0, company_address_vn, normal)

		sheet.merge_range('C1:E1', self._get_icf_header_text1_vn(), merge_format)
		sheet.merge_range('C2:E2', self._get_icf_header_text2_vn(), merge_format)

		sheet.write(2, 0, self._get_icf_header_text3_vn(), normal_bold)
		sheet.write(3, 0, self._get_icf_header_text4_vn(), normal_bold_italic)

		date_report_vn = self._get_year_report_vn(options)
		sheet.write(4, 0, date_report_vn, normal_bold)

		sheet.write(5, 4, self._get_icf_header_text5_vn(), normal_italic)

	def _get_b03_body_format(self, workbook):
		header = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'bold': True,
									  'font_size': 10, 'border': 1})
		bold = workbook.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'bold': True, 'font_size': 10,
									'border': 1})
		bold_center = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter',
										   'bold': True, 'font_size': 10, 'border': 1})
		bold_right = workbook.add_format({'font_name': 'Arial', 'align': 'right', 'valign': 'vcenter',
										  'bold': True, 'font_size': 10, 'border': 1, 'num_format': '#,##0.00 "₫"'})
		normal = workbook.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'font_size': 10, 'border': 1})
		normal_center = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter',
											 'font_size': 10, 'border': 1})
		normal_right = workbook.add_format({'font_name': 'Arial', 'align': 'right', 'valign': 'vcenter',
											'font_size': 10, 'border': 1, 'num_format': '#,##0.00 "₫"'})
		return header, bold, bold_center, bold_right, normal, normal_center, normal_right

	def _get_b03_custom_lines(self, options, line_id=None):
		# self = self.with_context(debug=True) # only for debug
		
		ctx = self._set_context(options)
		ctx.update(excel_report=True)
		lines = self.with_context(ctx)._get_lines(options, line_id=line_id)
		
		line_ids = [str(line['id']) for line in lines]
		line_codes = self._get_report_show_status(line_ids)

		for idx, line in enumerate(lines):
			if not line_codes.get(str(line['id'])):
				del lines[idx]

		return lines

	def set_xlsxb03_body(self, options, workbook, sheet):
		
		header, bold, bold_center, bold_right, normal, normal_center, normal_right = self._get_b03_body_format(workbook)

		sheet.write(6, 0, "Chỉ tiêu", header)
		sheet.write(6, 1, "Mã số", header)
		sheet.write(6, 2, "Thuyết minh", header)
		sheet.write(6, 3, "Năm nay", header)
		sheet.write(6, 4, "Năm trước", header)

		for i in range(5):
			sheet.write(7, i, i + 1, header)

		lines = self._get_b03_custom_lines(options)

		idx_row = 8
		for line in lines:
			lvl = line['level']
			if lvl <= 1:
				format_cell = bold
				format_code_cell = bold_center
				format_value = bold_right
			else:
				format_cell = normal
				format_code_cell = normal_center
				format_value = normal_right

			code_list = line['code'].split('_')
			code = code_list[1]
			if lvl == 0:
				if code in ['I', 'II', 'III']:
					code = ''
			else:
				if code == 'x':
					code = ''

			sheet.write(idx_row, 0, line['name'], format_cell)
			sheet.write(idx_row, 1, code, format_code_cell)
			sheet.write(idx_row, 2, '', normal)

			columns = line['columns']

			this_value = ''
			if columns[0]['name'] != '':
				this_value = columns[0].get('no_format_name',0)

			prev_value = ''
			if len(columns) > 1 and columns[1]['name'] != '':
				prev_value = columns[1].get('no_format_name',0)

			sheet.write(idx_row, 3, this_value, format_value)
			sheet.write(idx_row, 4, prev_value, format_value)

			idx_row += 1

		bold = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'bold': True,
									'font_size': 10})
		normal = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'font_size': 10})

		footer_vn = self._get_footer_vn()
		sheet.write(idx_row + 1, 1, footer_vn[0][0], bold)
		sheet.write(idx_row + 1, 2, footer_vn[1][0], bold)
		sheet.write(idx_row + 1, 3, footer_vn[2][0], bold)
		sheet.write(idx_row + 4, 1, footer_vn[0][1], normal)
		sheet.write(idx_row + 4, 2, footer_vn[1][1], normal)
		sheet.write(idx_row + 4, 3, footer_vn[2][1], normal)

	def get_xlsxb03(self, options, response):
		output = io.BytesIO()
		workbook = xlsxwriter.Workbook(output, {'in_memory': True})
		sheet = workbook.add_worksheet("INDIRECT CF")

		self._set_b03_column(sheet)
		self._set_b03_row(sheet)

		self.set_xlsxb03_header(options, workbook, sheet)
		self.set_xlsxb03_body(options, workbook, sheet)

		workbook.close()
		output.seek(0)
		response.stream.write(output.read())
		output.close()
	# ======================================= END OF CASH FLOW XLSX REPORT =======================================

class AccountFinancialHtmlReportLine(models.Model):
	_inherit = 'account.financial.html.report.line'

	date_maturity_domain = fields.Char(string="Due Date Domain")
	period = fields.Selection([
		('current', _("Ending")),
		('previous', _("Beginning")),
		('cur_prev', _("Ending - Beginning")),
		('prev_cur', _("Beginning - Ending")),

		('init-end', _("Initial Balance - Ending")),
		('end-init', _("Ending - Initial Balance")),
	], string=_("Period"), default='current', required=True)
	source = fields.Selection([
		('aml', _("Journal Items")),
		('gl', _("General Ledger")),
		('bs_01_dn', _("Balance Sheet 03 DN")),
	], string=_("Source"), default='aml', required=True)
	show = fields.Boolean(default=True, string="Show")
	calc_type = fields.Selection([
		('drb', "DRB"),
		('drb_neg', "DRB Negative"),
		('crb', "CRB"),
		('crb_neg', "CRB Negative"),
	], string="Calculation Type", default='drb')
	group_line = fields.Selection([
		('account', "Account"),
		('partner', "Partner"),
	], string="Grouping Line", default='account')
	zero_if_negative = fields.Boolean(string="Set as 0 when balance was negative", default=False)

	def _extend_lines(self, list_lines):
		res = []
		# line_ids = [line.get('id') for line in list_lines]
		line_ids = []
		for line in list_lines:
			if type(line.get('id'))==int:
				line_ids.append(line.get('id'))
		if len(line_ids):
			lines = self.browse(line_ids)
			# TO REMOVE
			line_to_remove = self.search([('show','=',False), ('id','in',line_ids)])
			try:
				if not self._context.get('debug'):
					
					if self._context.get('excel_report') and self._context.get('fetch_outside_origin_report'):
						line_to_remove = lines.filtered(lambda r: False==True)
					else:
						line_to_remove = lines.filtered(lambda r: r.show==False)
					
				else:
					# if from excel report then show all
					line_to_remove = lines.filtered(lambda r: False==True)
				
			except MissingError as e:
				line_to_remove = self.env['account.financial.html.report.line']
				pass
			
			res_lines = lines - line_to_remove
			for line in list_lines:
				_logger.info("%s before int" % (line,))
				line_id = line.get('id')
				# if line.get('id') not in line_to_remove.ids and type(line.get('id'))!=int:
				# print(line.get('id'), 'eeeeeeeeeeeeeee')
				# if line.get('id') and type(line.get('id'))!=int:	
				# 	line_id = line.get('id').split('_')
				# 	line_id = int(line_id[-1])
				# 	line.update({
				# 		'id': line_id,
				# 	})
				_logger.info("%s before int print line_id %s" % (line_id,type(line_id),))
				if line.get('id') not in line_to_remove.ids:
				# if type(line_id)==int:
					
					caret_options = line.get('caret_options')
					_logger.info("%s after int" % (line,))
					if caret_options and caret_options=='partner_id':
						l = lines.filtered(lambda r:r.id==line.get('financial_group_line_id'))
					elif caret_options=='account.account':
						try:
							l = lines.filtered(lambda r:r.id==line.get('id'))
							l.mapped('code') #just test if raise error only purpose
						except MissingError as e:
							l = lines.filtered(lambda r:r.id==line.get('parent_id'))
					else:
						l = lines.filtered(lambda r:r.id==line_id)
					columns = line.get('columns')
					code = ''
					l_code = l.mapped('code')
					clean_l_code = [l for l in l_code if l]
					if l_code:
						code = ','.join(clean_l_code)
					line.update({
						'code': code,
					})
					res.append(line)
						
		return res

	def _compute_line(self, currency_table, financial_report, group_by=None, domain=[]):
		
		res = super(AccountFinancialHtmlReportLine, self)._compute_line(currency_table=currency_table, financial_report=financial_report, group_by=group_by, domain=domain)
		res['crb'] = res.get('credit')-res.get('debit')
		res['drb'] = res.get('debit')-res.get('credit')
		return res

	
	def _get_lines(self, financial_report, currency_table, options, linesDicts):
		
		sup = super(AccountFinancialHtmlReportLine, self.with_context(financial_report=financial_report))._get_lines(financial_report, currency_table, options, linesDicts)
		customized_reports = self.env.ref('vn_vas_report.account_financial_report_b01') + self.env.ref('vn_vas_report.account_financial_report_pnl_b02') + self.env.ref('vn_vas_report.account_financial_report_icf_b03')
		print('forever loop')
		if financial_report.id in customized_reports.ids:
			sup = self.with_context(financial_report=financial_report)._extend_lines(sup)
			for rec in sup:
				if 'financial_group_line_id' in rec:
					group_line = self.env['account.financial.html.report.line'].browse(rec['financial_group_line_id'])
					if group_line.zero_if_negative and rec['columns'][0]['no_format_name'] < 0.0:
						rec['columns'][0]['no_format_name'] = 0
						rec['columns'][0]['name'] = 0
		
		return sup

	def _get_previous_date(self, date_from_str, date_to_str):
		""" Get previous date for comparison """
		date_from = datetime.strptime(date_from_str, DEFAULT_SERVER_DATE_FORMAT)
		date_to = datetime.strptime(date_to_str, DEFAULT_SERVER_DATE_FORMAT)

		def _get_date_from_diff(diff_month):
			custom_date_from = date_from - relativedelta(months=diff_month)
			custom_date_to = date_to - relativedelta(months=diff_month)

			_result_date_from = custom_date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
			_result_date_to = custom_date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)

			is_last_day = date_to.day == monthrange(date_to.year, date_to.month)[1]
			if is_last_day:
				new_last_day = monthrange(custom_date_to.year, custom_date_to.month)[1]
				_result_date_to = '%d-%d-%d' % (custom_date_to.year, custom_date_to.month, new_last_day)
			return _result_date_from, _result_date_to

		if self._context.get('periods'):
			periods = self._context['periods'][0]
			previous_date_to = datetime.strptime(periods['date_to'], DEFAULT_SERVER_DATE_FORMAT)
			previous_date_from = datetime.strptime(periods['date_from'], DEFAULT_SERVER_DATE_FORMAT)

			date_from_diff = relativedelta(date_from, previous_date_from)

			session = request.httprequest.session
			if previous_date_from < date_from:
				diff_month = (date_from_diff.years * 12) + date_from_diff.months
				session['icf_diff_month'] = diff_month
				result_date_from = previous_date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
				result_date_to = previous_date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)
			else:
				diff_month = session.get('icf_diff_month')
				result_date_from, result_date_to = _get_date_from_diff(diff_month)
		else:
			tmp_date_to = date_to + timedelta(days=1)
			date_from_diff = relativedelta(tmp_date_to, date_from)

			diff_month = (date_from_diff.years * 12) + date_from_diff.months
			result_date_from, result_date_to = _get_date_from_diff(diff_month)

		return result_date_from, result_date_to

	def _get_aml_domain(self):
		if self.financial_report_id.date_range:
			result = (safe_eval(self.domain or '[]') or []) + (self._context.get('filter_domain') or []) + (
						self._context.get('group_domain') or [])
			ctx_date_from = self._context.get('date_from')
			ctx_date_to = self._context.get('date_to')

			if ctx_date_from and ctx_date_from:
				result += [('date','>=',ctx_date_from),('date','<=',ctx_date_to)]

			if self.date_maturity_domain:
				
				date_to = datetime.strptime(self._context['date_to'], DEFAULT_SERVER_DATE_FORMAT) # don't remove this, used for date_maturity_domain eval

				one_year = False
				if '-01-01' in ctx_date_from and '-12-31' in ctx_date_to:
					# if filter 1 year
					one_year = True
				is_last_day = date_to.day == monthrange(date_to.year, date_to.month)[1]

				dm_domain = eval(self.date_maturity_domain)
				import re
				vv = re.match('months\=(?P<_0>.+)', self.date_maturity_domain)
				months = re.findall('months=([0-9.]*[0-9]+)',self.date_maturity_domain)
				days = 360
				if len(months):
					months = months[0]
					days = int(months) * 30
				if is_last_day:
					for idx, dm in enumerate(dm_domain):
						dm_date = datetime.strptime(dm[2], DEFAULT_SERVER_DATE_FORMAT)
						dm_last_day = monthrange(dm_date.year, dm_date.month)[1]
						new_dm = list(dm)
						# if using range from current access date
						# if one_year:
						# 	date_from = datetime.strptime(ctx_date_from, '%Y-%m-%d')
						# 	month_date_from = date_from.strftime('%m')
						# 	# new_dm[2] = '%d-%d-%d' % (dm_date.year, date_from.month, dm_last_day)
						# 	delta = (datetime.now() + timedelta(days=days))
						# 	mr_last = str(monthrange(delta.year, delta.month)[1])
						# 	dformat = '{y}-{m}-%s' % (mr_last.rjust(2,'0'),)
						# 	dformat = dformat.format(y='%Y',m='%m')
						# 	new_dm[2] = delta.strftime(dformat)
							
						# else:
						# 	new_dm[2] = '%d-%d-%d' % (dm_date.year, dm_date.month, dm_last_day)
						new_dm[2] = '%d-%d-%d' % (dm_date.year, dm_date.month, dm_last_day)
						
						new_dm = tuple(new_dm)
						dm_domain[idx] = new_dm

				result += dm_domain
			
			state_ctx = self._context.get('state')
			if state_ctx:
				result += [('move_id.state','=',state_ctx)]

			return result
		else:
			result = (safe_eval(self.domain or '[]') or []) + (self._context.get('filter_domain') or []) + (
						self._context.get('group_domain') or [])
			ctx_date_to = self._context.get('date_to')
			ctx_date_from = self._context.get('date_from')
			if ctx_date_to:
				result += [('date','<=',ctx_date_to)]
				if self.date_maturity_domain:
				
					date_to = datetime.strptime(self._context['date_to'], DEFAULT_SERVER_DATE_FORMAT) # don't remove this, used for date_maturity_domain eval

					one_year = False
					if '-01-01' in ctx_date_from and '-12-31' in ctx_date_to:
						# if filter 1 year
						one_year = True
					is_last_day = date_to.day == monthrange(date_to.year, date_to.month)[1]

					dm_domain = eval(self.date_maturity_domain)
					import re
					vv = re.match('months\=(?P<_0>.+)', self.date_maturity_domain)
					months = re.findall('months=([0-9.]*[0-9]+)',self.date_maturity_domain)
					days = 360
					if len(months):
						months = months[0]
						days = int(months) * 30
					if is_last_day:
						for idx, dm in enumerate(dm_domain):
							dm_date = datetime.strptime(dm[2], DEFAULT_SERVER_DATE_FORMAT)
							dm_last_day = monthrange(dm_date.year, dm_date.month)[1]
							new_dm = list(dm)
							# if using range from current access date
							# if one_year:
							# 	date_from = datetime.strptime(ctx_date_from, '%Y-%m-%d')
							# 	month_date_from = date_from.strftime('%m')
							# 	# new_dm[2] = '%d-%d-%d' % (dm_date.year, date_from.month, dm_last_day)
							# 	delta = (datetime.now() + timedelta(days=days))
							# 	mr_last = str(monthrange(delta.year, delta.month)[1])
							# 	dformat = '{y}-{m}-%s' % (mr_last.rjust(2,'0'),)
							# 	dformat = dformat.format(y='%Y',m='%m')
							# 	new_dm[2] = delta.strftime(dformat)
								
							# else:
							# 	new_dm[2] = '%d-%d-%d' % (dm_date.year, dm_date.month, dm_last_day)
							new_dm[2] = '%d-%d-%d' % (dm_date.year, dm_date.month, dm_last_day)
							
							new_dm = tuple(new_dm)
							dm_domain[idx] = new_dm

					result += dm_domain
			
			return result



	def _get_bs_value(self, financial_report, date_from, date_to):
		""" Get value for Indirect Cash Flow from Balance Sheet as source """
		splitted_formulas = self.formulas.split('=')
		formulas = splitted_formulas[1].strip().split('.')
		bs_code = formulas[0]
		report_line = self.env['account.financial.html.report.line'].search([('code', '=', bs_code)])

		options = self._build_custom_options(date_from, date_to)
		options['comparison'] = {
			'date_from': date_from,
			'date_to': date_to,
			'filter': 'no_comparison',
		}
		linesDicts = [[{}], [{}]]
		lines = report_line.with_context(date_from=date_from, date_to=date_to)._get_lines(financial_report=financial_report,
																						  currency_table=None,
																						  options=options,
																						  linesDicts=linesDicts)
		bs_value = 0
		for line in lines:
			if line.get('code') == bs_code:
				columns = line.get('columns')
				if isinstance(columns, list):
					bs_value = columns[0].get('no_format_name',0)
				break
			elif bs_code in line.get('code') and bs_code+"," in line.get('code') and line.get('class')=='total':
				columns = line.get('columns')
				if isinstance(columns, list):
					bs_value = columns[0].get('no_format_name',0)
				break
		return bs_value

	def _get_bs_01_dn_balance(self):
		""" Get value for Indirect Cash Flow from Balance Sheet as source """
		f_report = self.env.ref('vn_vas_report.account_financial_report_b01')
		date_from = self._context['date_from']
		date_to = self._context['date_to']
		
		if self.period == 'previous':
			date_from, date_to = self._get_previous_date(date_from, date_to)

		bs_value = self._get_bs_value(f_report, date_from, date_to)

		if self.period in ['cur_prev', 'prev_cur']:
			
			date_from, date_to = self._get_previous_date(date_from, date_to)
			bs_prev_value = self._get_bs_value(f_report, date_from, date_to)
			
			if self.period == 'cur_prev':
				return bs_value - bs_prev_value
			else:
				return bs_prev_value - bs_value

		return bs_value

	def _build_custom_options(self, date_from, date_to):
		options = {
			'date': {
				'date_from': date_from,
				'date_to': date_to,
				'mode':'range',
			},
			'partner': None,
			'unfold_all': False,
			'unfolded_lines': [],
			'unposted_in_period': True
		}

		return options

	def _get_gl_balance(self):
		""" Get value for Indirect Cash Flow from General Ledger as source """
		try:
			domain = self._get_aml_domain()
			
			aml = self.env['account.move.line'].search(domain, limit=1)

			date_from = self._context['date_from']
			date_to = self._context['date_to']

			if self.period == 'previous':
				date_from, date_to = self._get_previous_date(date_from, date_to)
			
			options = self._build_custom_options(date_from, date_to)
			

			if aml:
				gl_obj = self.env['account.general.ledger']
				account = aml.account_id
				line_id = 'account_%d' % (account.id,)																																																	

				# gl = gl_obj.with_context(date_from=date_from, date_to=date_to)._get_custom_lines(options, line_id=line_id)
				options['unfolded_lines'] = ['account_%s' % (account.id,)]
				gl = gl_obj.with_context(date_from=date_from, date_to=date_to, no_format=1)._get_general_ledger_lines(options, line_id=line_id)
				
				def map_unfolded(gls):
					initial = None
					total = None
					return gls[1],gls[0]

				initial,total = map_unfolded(gl)

				if self.formulas:
					formula = self.formulas.split('.')
					key = formula[1]
					if self.period in ['cur_prev', 'prev_cur','init-end','end-init']:
						if self.period in ['cur_prev','prev_cur']:
							date_from, date_to = self._get_previous_date(date_from, date_to)
							gl_prev = gl_obj.with_context(date_from=date_from, date_to=date_to)._get_custom_lines(options, line_id=line_id)
							if self.period == 'cur_prev':
								return gl[key] - gl_prev[key]
							else:
								return gl_prev[key] - gl[key]
						else:
							init_cols = initial.get('columns')
							end_cols = total.get('columns')
							if self.period == 'init-end':
								# return gl['initial_balance'] - gl['balance']
								
								return init_cols[3].get('name') - end_cols[3].get('name')
							elif self.period == 'end-init':
								# return gl['balance'] - gl['initial_balance']
								return end_cols[3].get('name') - init_cols[3].get('name')
						
					else:
						return gl[key]
				
			return 0
		except Exception as E:
			_logger.error(E)
			_logger.info('Return as 0 _get_gl_balance')
			return 0

	def _get_group_balance(self):
		""" Get value non negative based from group_line. Used in Balance Sheet (B01) """
		aml_domain = self._get_aml_domain()
		aml_ids = self.env['account.move.line'].search(aml_domain)
		
		balance_list = []
		
		
		def get_balance(_aml_ids):
			balance = sum(_aml_ids.mapped('balance'))
			
			if self.calc_type == 'drb':
				# DRB, debit - credit -> sum.balance. DRB always non negative
				balance = sum(_aml_ids.mapped('debit')) - sum(_aml_ids.mapped('credit'))            
				if self.zero_if_negative and balance < 0.0:
					balance = 0
			elif self.calc_type == 'drb_neg':
				balance = sum(_aml_ids.mapped('debit')) - sum(_aml_ids.mapped('credit'))
				if balance > 0:
					balance *= -1
			elif self.calc_type == 'crb_neg':
				# CRB, credit - debit -> -sum.balance
				balance = sum(_aml_ids.mapped('credit')) - sum(_aml_ids.mapped('debit'))
				if balance > 0:
					balance *= -1
			elif self.calc_type == 'crb':
				balance = sum(_aml_ids.mapped('credit')) - sum(_aml_ids.mapped('debit'))
				if self.zero_if_negative and balance < 0.0:
					balance = 0
			return balance

		if self.group_line == 'account':
			account_ids = aml_ids.mapped('account_id')
			for account_id in account_ids:
				filtered_aml_ids = aml_ids.filtered(lambda r: r.account_id.id == account_id.id and r.parent_state=='posted')
				balance_list.append(get_balance(filtered_aml_ids))
		elif self.group_line == 'partner':
			partner_ids = aml_ids.mapped('partner_id')
			for partner_id in partner_ids:
				filtered_aml_ids = aml_ids.filtered(lambda r: r.partner_id.id == partner_id.id)
				balance_list.append(get_balance(filtered_aml_ids))
			# handling if any aml that partner_id=None
			no_partner_filtered_aml_ids = aml_ids.filtered(lambda r: r.partner_id.id == False)
			if len(no_partner_filtered_aml_ids):
				balance_list.append(get_balance(no_partner_filtered_aml_ids))
		else:
			balance_list.append(get_balance(aml_ids))
		
		return sum(balance_list)


class CustomFormulaLine(object):

	def __init__(self, obj, currency_table, financial_report, type='balance', linesDict=None):
		obj_is_dict = False
		try:
			obj.source
		except:
			obj_is_dict = isinstance(obj,dict)

		if linesDict is None:
			linesDict = {}
		
		fields = dict((fn, 0.0) for fn in ['debit', 'credit', 'balance'])
		if type == 'balance':
			fields = obj._get_balance(linesDict, currency_table, financial_report)[0]
			linesDict[obj.code] = self
		elif type in ['sum', 'sum_if_pos', 'sum_if_neg']:
			if type == 'sum_if_neg':
				obj = obj.with_context(sum_if_neg=True)
			if type == 'sum_if_pos':
				obj = obj.with_context(sum_if_pos=True)
			if obj._name == 'account.financial.html.report.line':
				fields = obj._get_sum(currency_table, financial_report)
				self.amount_residual = fields['amount_residual']
				
			elif obj._name == 'account.move.line':
				self.amount_residual = 0.0
				field_names = ['debit', 'credit', 'balance', 'amount_residual', 'crb','drb']
				res = obj.env['account.financial.html.report.line']._compute_line(currency_table, financial_report)
				for field in field_names:
					fields[field] = res[field]
				self.amount_residual = fields['amount_residual']
		elif type == 'not_computed':
			for field in fields:
				fields[field] = obj.get(field, 0)
			self.amount_residual = obj.get('amount_residual', 0)
		elif type == 'null':
			self.amount_residual = 0.0
		self.balance = fields['balance']
		self.credit = fields['credit']
		self.debit = fields['debit']

		if fields.get('crb'):
			self.crb = fields['crb']
		if fields.get('drb'):
			self.drb = fields['drb']
		if obj is not None:
			if obj_is_dict==False and obj.source in ['gl','bs_01_dn']:
				try:
					if obj.source == 'gl':
						self.balance = obj._get_gl_balance()
					elif obj.source == 'bs_01_dn':
						self.balance = obj.with_context(fetch_outside_origin_report=True)._get_bs_01_dn_balance()

						
					# elif obj.source == 'aml' and obj.group_line:
					# 	self.balance = obj._get_group_balance()
				except Exception as E:
					_logger.error(E)
					_logger.info('Passing Raise Exception')
					pass
			
			elif obj_is_dict==False and obj.source == 'aml' and obj.calc_type:
				if obj.group_line:
					self.balance = obj._get_group_balance()
				else:
					if fields.get('crb') or fields.get('drb'):
						if 'crb' in obj.calc_type:
							# if crb
							self.balance = self.crb
						elif 'drb' in obj.calc_type:
							# if drb
							self.balance = self.drb

# patching
FormulaLine.__init__ = CustomFormulaLine.__init__
