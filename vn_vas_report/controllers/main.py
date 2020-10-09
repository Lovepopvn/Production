# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import content_disposition, request
from odoo.addons.web.controllers.main import _serialize_exception
from odoo.tools import html_escape
from odoo.addons.account_reports.controllers.main import FinancialReportController

import json


class FinancialReportControllerCustom(FinancialReportController):

    @http.route('/account_reports', type='http', auth='user', methods=['POST'], csrf=False)
    def get_report(self, model, options, output_format, token, financial_id=None, **kw):
        uid = request.session.uid
        report_obj = request.env[model].with_user(uid)
        options = json.loads(options)
        if financial_id and financial_id != 'null':
            report_obj = report_obj.browse(int(financial_id))
        report_name = report_obj.get_report_filename(options)
        try:
            if output_format == 'xlsx2':
                response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition(report_name + '.xlsx'))
                    ]
                )
                report_obj.get_xlsx2(options, response)

            if output_format == 'xlsx':
                response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition(report_name + '.xlsx'))
                    ]
                )
                if report_obj.id == request.env.ref('vn_vas_report.account_financial_report_pnl_b02').id:
                    # if PNL CP
                    # report.get_xlsx_pnl(options, response)
                    report_obj._get_xlsx_pnl(options, response)
                elif report_obj.id == request.env.ref('vn_vas_report.account_financial_report_b01').id:
                    report_obj.with_context(lang='vi_VN').get_xlsxb01(options, response)
                elif report_obj.id == request.env.ref('vn_vas_report.account_financial_report_icf_b03').id:
                    report_obj.with_context(lang='vi_VN').get_xlsxb03(options, response)
                else:
                    report_obj.get_xlsx(options, response)
            if output_format == 'pdf':
                response = request.make_response(
                    report_obj.with_context(lang='vi_VN').get_pdf(options),
                    headers=[
                        ('Content-Type', 'application/pdf'),
                        ('Content-Disposition', content_disposition(report_name + '.pdf'))
                    ]
                )
            if output_format == 'xml':
                content = report_obj.get_xml(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', 'application/vnd.sun.xml.writer'),
                        ('Content-Disposition', content_disposition(report_name + '.xml')),
                        ('Content-Length', len(content))
                    ]
                )
            if output_format == 'xaf':
                content = report_obj.get_xaf(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', 'application/vnd.sun.xml.writer'),
                        ('Content-Disposition', 'attachment; filename=' + report_name + '.xaf;'),
                        ('Content-Length', len(content))
                    ]
                )
            if output_format == 'txt':
                content = report_obj.get_txt(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', 'text/plain'),
                        ('Content-Disposition', content_disposition(report_name + '.txt')),
                        ('Content-Length', len(content))
                    ]
                )
            if output_format == 'csv':
                content = report_obj.get_csv(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', 'text/csv'),
                        ('Content-Disposition', 'attachment; filename=' + report_name + '.csv;'),
                        ('Content-Length', len(content))
                    ]
                )
            if output_format == 'zip':
                content = report_obj._get_zip(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', 'application/zip'),
                        ('Content-Disposition', 'attachment; filename=' + report_name + '.zip'),
                    ]
                )
                # Adding direct_passthrough to the response and giving it a file
                # as content means that we will stream the content of the file to the user
                # Which will prevent having the whole file in memory
                response.direct_passthrough = True
            response.set_cookie('fileToken', token)
            return response
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))
