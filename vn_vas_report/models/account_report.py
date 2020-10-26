# -*- coding: utf-8 -*-
import lxml
from odoo import models, fields, api, _
import json
import io
import logging
import lxml.html
import datetime
import ast

from dateutil.relativedelta import relativedelta

try:
	from odoo.tools.misc import xlsxwriter
except ImportError:
	# TODO saas-17: remove the try/except to directly import from misc
	import xlsxwriter

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, pycompat, config, date_utils
from odoo.osv import expression
from babel.dates import get_quarter_names
from odoo.tools.misc import formatLang, format_date
from odoo.addons.web.controllers.main import clean_action
from odoo.exceptions import UserError
from datetime import datetime
from odoo.addons.vn_vas_report.models.account_financial_html_report import AccountFinancialHtmlReport

class AccountReportCustom(models.AbstractModel):
	"""inherit account report"""
	_inherit = 'account.report'

	def _get_bs_footer(self, url):
		return """<!DOCTYPE html>
			<base href=%s>
			<html style="height: 0;">
				<head>
					<link type="text/css" rel="stylesheet" href="/web/content/827-683c402/web.report_assets_pdf.0.css"/>
					<link type="text/css" rel="stylesheet" href="/web/content/828-044ab30/web.report_assets_common.0.css"/>
					<link type="text/css" rel="stylesheet" href="/web/content/829-044ab30/web.report_assets_common.1.css"/>
					<meta charset="utf-8"/>
					<script>
						function subst() {
							var vars = {};
							var x = document.location.search.substring(1).split('&');
							for (var i in x) {
								var z = x[i].split('=', 2);
								vars[z[0]] = unescape(z[1]);
							}
							var fromPage = document.getElementsByClassName('page');
							for(var j = 0; j<fromPage.length; j++)
								fromPage[j].textContent = vars['sitepage'];
							var toPage = document.getElementsByClassName('topage');
							for(var j = 0; j<toPage.length; j++)
								toPage[j].textContent = vars['sitepages'];
	
							var index = vars['webpage'].split('.', 4)[3]
							var header = document.getElementById('minimal_layout_report_headers');
							if(header !== null){
								var companyHeader = header.children[index];
								header.textContent = '';
								header.appendChild(companyHeader);
							}
							var footer = document.getElementById('minimal_layout_report_footers');
							if(footer !== null){
								var companyFooter = footer.children[index];
								footer.textContent = '';
								footer.appendChild(companyFooter);
							}
						}
					</script>
				</head>
				<body class="container" onload="subst()">
					<div class="header">
						<div class="row">
							<div class="col-2 offset-10 text-right">
								<ul class="list-inline">
									<li class="list-inline-item"><span class="page"></span></li>
									<li class="list-inline-item">/</li>
									<li class="list-inline-item"><span class="topage"></span></li>
								</ul>
							</div>
						</div>
					</div>
					<div class="article"></div>
				</body>
			</html>""" % (url,)

	def get_pdf(self, options, minimal_layout=True):
		bs_report = self.env.ref('vn_vas_report.account_financial_report_b01')
		icf_report = self.env.ref('vn_vas_report.account_financial_report_icf_b03')
		if self in [bs_report, icf_report]:
			# custom report footer for balance sheet
			if not config['test_enable']:
				self = self.with_context(commit_assetsbundle=True)

			base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env[
				'ir.config_parameter'].sudo().get_param('web.base.url')
			rcontext = {
				'mode': 'print',
				'base_url': base_url,
				'company': self.env.user.company_id,
			}

			body = self.env['ir.ui.view'].render_template(
				"account_reports.print_template",
				values=dict(rcontext),
			)
			body_html = self.with_context(print_mode=True).get_html(options)

			body = body.replace(b'<body class="o_account_reports_body_print">',
								b'<body class="o_account_reports_body_print">' + body_html)
			if minimal_layout:
				header = ''
				# footer = self.env['ir.actions.report'].render_template("web.internal_layout", values=rcontext)
				spec_paperformat_args = {'data-report-margin-top': 10, 'data-report-header-spacing': 10}
				# footer = self.env['ir.actions.report'].render_template("web.minimal_layout",
				# 													   values=dict(rcontext, subst=True, body=footer))

			landscape = False
			if len(self.with_context(print_mode=True).get_header(options)[-1]) > 5:
				landscape = True

			base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
			new_footer = self._get_bs_footer(base_url).encode()

			return self.env['ir.actions.report']._run_wkhtmltopdf(
				[body],
				header=header, footer=new_footer,
				landscape=landscape,
				specific_paperformat_args=spec_paperformat_args
			)
		else:
			return super(AccountReportCustom, self).get_pdf(options, minimal_layout=minimal_layout)

	# def _get_reports_buttons(self):
	# 	# ------------------------ set button for Balance Sheet B01-DN ------------------------
	# 	b01 = self.env.ref('vn_vas_report.account_financial_report_b01')
	# 	if self._context.get('id') == b01.id:
	# 		return [{'name': _('Print Preview'), 'action': 'print_pdf'}, {'name': _('Export (XLSX)'), 'action': 'print_xlsxb01'}]
	# 	# -------------------------------------------------------------------------------------
	# 	# return [{'name': _('Print Preview'), 'action': 'print_pdf'}, {'name': _('Export (XLSX)'), 'action': 'print_xlsx'}, {'name': _('MAKE OFFICIAL FORM (XLSX)'), 'action': 'print_xlsx2'}]
	# 	return [{'name': _('Print Preview'), 'action': 'print_pdf'}, {'name': _('Export (XLSX)'), 'action': 'print_xlsx'}]


	# def _apply_date_filter(self, options):
	# 	""" 
	# 	Replace _apply_date_filter(), default comparison should be previous period 
	# 	"""
	# 	super()._apply_date_filter(options)

	# 	b01 = self.env.ref('vn_vas_report.account_financial_report_b01')
	# 	pnl01 = self.env.ref('vn_vas_report.account_financial_report_pnl_b02')
	# 	custom_reports = b01+pnl01
	# 	if type(self) == AccountFinancialHtmlReport:
	# 		if self not in custom_reports:
	# 			super(AccountFinancialHtmlReport, self)._apply_date_filter(options)
	# 			return
	# 	cmp_filter = options['comparison']['filter']
	# 	if cmp_filter == 'no_comparison':
	# 		cmp_filter = 'previous_period'
	# 		options['comparison']['filter'] = 'previous_period'
	# 	period_vals = self._get_dates_period(options, date_from, date_to, period_type)
	# 	periods = []
	# 	number_period = options['comparison'].get('number_period', 1) or 0
	# 	for index in range(0, number_period):
	# 		if cmp_filter == 'previous_period':
	# 			period_vals = self._get_dates_previous_period(options, period_vals)
	# 		else:
	# 			period_vals = self._get_dates_previous_year(options, period_vals)
	# 		periods.append(create_vals(period_vals))

	# 	if len(periods) > 0:
	# 		options['comparison'].update(periods[0])
		
	# 	options['comparison']['periods'] = periods
	# 	options['hide_no_comparison'] = True

	def get_xlsx2(self, options, response):
		output = io.BytesIO()
		workbook = xlsxwriter.Workbook(output, {'in_memory': True})
		sheet = workbook.add_worksheet(self._get_report_name()[:31])
		sheet.hide_gridlines(2)
		date_default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'num_format': 'yyyy-mm-dd'})
		date_default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': 'yyyy-mm-dd'})
		default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
		default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})
		title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
		super_col_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'align': 'center'})
		right = workbook.add_format({'font_name': 'Arial', 'align': 'right'})
		right_small = workbook.add_format({'font_name': 'Arial', 'align': 'right', 'font_size': 10})
		right_bold = workbook.add_format({'font_name': 'Arial', 'align': 'right', 'bold': True})
		normal = workbook.add_format({'font_name': 'Arial', 'bold': True})
		normal_border = workbook.add_format({'font_name': 'Arial', 'bold': True, 'border': 1})
		normal_border_center = workbook.add_format({'font_name': 'Arial', 'bold': True, 'border': 1, 'align': 'center'})
		normal_title = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 14})
		level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666'})
		level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666'})
		level_2_col1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
		level_2_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
		level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
		level_3_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
		level_3_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
		level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})

		#Set the first column width to 50
		sheet.set_column(0, 0, 5)
		sheet.set_column(1, 1, 50)
		sheet.set_column(2, 2, 20)
		sheet.set_column(3, 3, 25)
		sheet.set_column(4, 4, 20)
		sheet.set_column(5, 5, 20)
		sheet.set_column(6, 6, 20)
		sheet.write(0, 1,self.env.user.company_id.name, normal)
		# sheet.write(1, 1,self.env.user.company_id.street)
		# sheet.write(2, 1,self.env.user.company_id.city + " " +self.env.user.company_id.state_id.name+ " "+self.env.user.company_id.zip)
		sheet.write(4, 1,self.name  , normal_title)
		if self.id == 2 :
				sheet.write(5, 1,self.get_header(options)[0][1]['name'])
		elif self.id == 1 :
				sheet.write(5, 1,_('For the year ended {0}').format(self.get_header(options)[0][1]['name'][-4:]))
		elif self.id == 3 :
				sheet.write(5, 1,_('For the year ended {0}').format(self.get_header(options)[0][1]['name'][-4:]))
		super_columns = self._get_super_columns(options)
		y_offset = 8
		
		# sheet.write(y_offset, 0, 'Item', title_style)

		# Todo in master: Try to put this logic elsewhere
		x = super_columns.get('x_offset', 0)
		for super_col in super_columns.get('columns', []):
			cell_content = super_col.get('string', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
			x_merge = super_columns.get('merge')
			if x_merge and x_merge > 1:
				sheet.merge_range(0, x, 0, x + (x_merge - 1), cell_content, super_col_style)
				x += x_merge
			else:
				sheet.write(0, x, cell_content, super_col_style)
				x += 1
		for row in self.get_header(options):
			x = 0
			for column in row:
				colspan = column.get('colspan', 1)
			#     header_label = column.get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
			#     if colspan == 1:
			#         sheet.write(y_offset, x, header_label, title_style)
			#     else:
			#         sheet.merge_range(y_offset, x, y_offset, x + colspan - 1, header_label, title_style)
				x += colspan
			y_offset += 1
		ctx = self._set_context(options)
		ctx.update({'no_format':True, 'print_mode':True})
		lines = self.with_context(ctx)._get_lines(options)

		if options.get('hierarchy'):
			lines = self._create_hierarchy(lines)

		#write all data rows
		for y in range(0, len(lines)):
			level = lines[y].get('level')
			if lines[y].get('caret_options'):
				style = normal
				col1_style = normal
			elif level == 0:
				# y_offset += 1
				style = normal
				col1_style = normal
			elif level == 1:
				style = normal
				col1_style = normal
			elif level == 2:
				style = normal
				col1_style = 'total' in lines[y].get('class', '').split(' ') and level_2_col1_total_style or level_2_col1_style
			elif level == 3:
				style = normal
				col1_style = 'total' in lines[y].get('class', '').split(' ') and level_3_col1_total_style or level_3_col1_style
			else:
				style = normal
				col1_style = normal

			if 'date' in lines[y].get('class', ''):
				#write the dates with a specific format to avoid them being casted as floats in the XLSX
				sheet.write_datetime(y + y_offset, 1, lines[y]['name'],  normal_border)
			else:
				#write the first column, with a specific style to manage the indentation
				sheet.write(y + y_offset, 1, lines[y]['name'], normal_border)

			#write all the remaining cells
			# for x in range(1, len(lines[y]['columns']) + 1):
			for x in range(1, 2):
				this_cell_style = normal
				if 'date' in lines[y]['columns'][x - 1].get('class', ''):
					#write the dates with a specific format to avoid them being casted as floats in the XLSX
					this_cell_style = normal
					sheet.write_datetime(y + y_offset, x + lines[y].get('colspan', 1), lines[y]['columns'][x - 1].get('name', ''), normal_border)
				else:
					
					code = self.env['account.financial.html.report.line'].search([('id', '=', lines[y]['id'] )]).code
					if code:
						sheet.write(y + y_offset, x + lines[y].get('colspan', 1), code[-2:], normal_border)
					else:
						 sheet.write(y + y_offset, x + lines[y].get('colspan', 1), code, normal_border)
					sheet.write(y + y_offset, x + lines[y].get('colspan', 1)+1, '', normal_border)
					sheet.write(y + y_offset, x + lines[y].get('colspan', 1)+2, lines[y]['columns'][x - 1].get('name', ''), normal_border)
					if(len(lines[y]['columns'])>1):
						j=3
						for res in range(1,len(lines[y]['columns'])):
							sheet.write(y + y_offset, x + lines[y].get('colspan', 1) + j, lines[y]['columns'][res].get('name', ''), normal_border)
							x+=1
					else:
						sheet.write(y + y_offset, x + lines[y].get('colspan', 1)+3, '', normal_border)
		# sheet.write(y_offset + y + 2, 1, _('(*) Only applied to Joint stock company'))
		sheet.write(y_offset + y + 3, 1, _('Prepared By'), normal)
		sheet.write(y_offset + y + 3, 2, _('Chief Accountant'), normal)
		sheet.write(y_offset + y + 3, 4, _('General Director'), normal)
		sheet.write(y_offset + y + 4, 1, _('(Signature, full name)'))
		sheet.write(y_offset + y + 4, 2, _('(Signature, full name)'))
		sheet.write(y_offset + y + 4, 4, _('(Signature, full name)'))
		# sheet.write(y_offset + y + 7, 1, _('Practicing Certificate :'))
		# sheet.write(y_offset + y + 8, 1, _('Accounting service provider:'))
		format4 = workbook.add_format({'num_format': 'd-m-yyyy'})
		today = datetime.now()
		sheet.write(7, 1, _('Item') , normal_border_center)
		sheet.write(7, 2, _('Code') , normal_border_center)
		sheet.write(7, 3, _('Description') , normal_border_center)
		if(len(lines[y]['columns'])>1):
			j=4
			for res in range(1,len(lines[y]['columns'])):
				sheet.write(7, j, self.get_header(options)[0][res]['name'][-4:] , normal_border_center)
				j+=1
			sheet.write(7, j, self.get_header(options)[0][res+1]['name'][-4:] , normal_border_center)
		else:
			sheet.write(7, 4, self.get_header(options)[0][1]['name'][-4:] , normal_border_center)
			sheet.write(7, 5, _('Last Year') , normal_border_center)
		sheet.write(8, 1, '1' , normal_border_center)
		sheet.write(8, 2, '2' , normal_border_center)
		sheet.write(8, 3, '3' , normal_border_center)
		if(len(lines[y]['columns'])>1):
			sheet.write(0, 5+len(lines[y]['columns'])-2,_('Form B-02/DN') , right_bold)
			sheet.write(1, 5+len(lines[y]['columns'])-2,_('Issued in accordance with Circular No. 200/2014/TT-BTC'), right_small)
			sheet.write(2, 5+len(lines[y]['columns'])-2,_('dated 22 December, 2014 of the Ministry of Finance'), right_small)
			sheet.write(6, 5+len(lines[y]['columns'])-2,_('Unit : {0}').format(self.env.user.company_id.currency_id.name)  , right_bold)
			sheet.write(y_offset + y + 2, 5+len(lines[y]['columns'])-2,_('Prepared on %s %s %s') % (today.strftime('%d'), today.strftime('%m'), today.strftime('%Y')), right)
			j=4
			for res in range(1,len(lines[y]['columns'])):
				sheet.write(8, j, j , normal_border_center)
				j+=1
			sheet.write(8, j, j , normal_border_center)
		else:
			sheet.write(8, 4, '4' , normal_border_center)
			sheet.write(8, 5, '5' , normal_border_center)
			sheet.write(0, 5,_('Form B-02/DN') , right_bold)
			sheet.write(1, 5,_('Issued in accordance with Circular No. 200/2014/TT-BTC'), right_small)
			sheet.write(2, 5,_('dated 22 December, 2014 of the Ministry of Finance'), right_small)
			sheet.write(6, 5,  _('Unit : {0}').format(self.env.user.company_id.currency_id.name)  , right_bold)
			sheet.write(y_offset + y + 2, 5,_('Prepared on %s %s %s') % (today.strftime('%d'), today.strftime('%m'), today.strftime('%Y')),right)
		
		workbook.close()
		output.seek(0)
		response.stream.write(output.read())
		output.close()

	def print_xlsx2(self, options):
		return {
				'type': 'ir_actions_account_report_download',
				'data': {'model': self.env.context.get('model'),
						 'options': json.dumps(options),
						 'output_format': 'xlsx2',
						 'financial_id': self.env.context.get('id'),
						 }
				}
