from odoo import http
from odoo.http import content_disposition, request
from odoo.addons.web.controllers.main import _serialize_exception
import base64
import logging

_logger = logging.getLogger(__name__)


class VATDownload(http.Controller):
    @http.route('/vat_allocation_download', type='http', auth="user")
    def download_vat_allocation(self, model, id, filename=None, **kw):
        Model = request.env[model]
        res = Model.browse(int(id))
        filecontent = base64.b64decode(res.data_x or '')
        if not filecontent:
            return request.not_found()
        else:
            if not filename:
                filename = '%s_%s' % (model.replace('.', '_'), id)
            return request.make_response(
                filecontent,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', content_disposition(filename + '.xlsx'))
                ])

    @http.route('/vat_declaration_download', type='http', auth="user")
    def download_vat_declaration(self, model, id, filename=None, **kw):
        Model = request.env[model]
        res = Model.browse(int(id))
        filecontent = base64.b64decode(res.data_x or '')
        if not filecontent:
            return request.not_found()
        else:
            if not filename:
                filename = '%s_%s' % (model.replace('.', '_'), id)
            return request.make_response(
                filecontent,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', content_disposition(filename + '.xlsx'))
                ])
