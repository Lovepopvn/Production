from . import models
from . import controllers

import logging

from odoo import api, SUPERUSER_ID
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    report = env['ir.module.module'].search([('name', '=', 'l10n_vn_reports')])
    if report and report.state in ['installed']:
        raise UserError('Uninstall base module l10n_vn_reports first')

    parent = env.ref('l10n_vn.account_reports_vn_statements_menu')
    if parent:
        for child in parent.child_id:
            data = eval(child.action.context)
            if data.get('model') == 'account.financial.html.report':
                report = env[data.get('model')].browse(data.get('id'))
                if not report:
                    child.unlink()

def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    parent = env.ref('l10n_vn.account_reports_vn_statements_menu')
    if parent:
        for child in parent.child_id:
            data = eval(child.action.context)
            if data.get('model') == 'account.financial.html.report':
                report = env[data.get('model')].browse(data.get('id'))
                if not report:
                    child.unlink()
