# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.http_routing.models.ir_http import slugify
from odoo.tools.misc import xlsxwriter

import base64
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta



# months in (int, str) tuples
MONTHS = [(str(month), '%02d' % month) for month in list(range(1, 13))]

TIMEZONE_RELATIVEDELTA = relativedelta(hours=7)

STATES = [('draft', 'Draft'), ('calculated', 'Calculated')]
DEFAULT_STATE = STATES[0][0]



class COGSReport(models.Model):
    _name = 'cogs.report'
    _description = 'COGS Report'
    _order = 'date_to desc, id desc'


    @api.model
    def _get_available_years(self, initial_year=2020):
        now = datetime.now() + TIMEZONE_RELATIVEDELTA
        current_year = now.year
        available_years_int = list(range(initial_year, current_year + 1))
        available_years = [(str(year), str(year)) for year in available_years_int]
        return available_years


    def _validate_dates(self):
        for record in self:
            if not record.date_from or not record.date_to:
                raise ValidationError(_('You must select the year and month to calculate the data for.'))
            if record.date_from + TIMEZONE_RELATIVEDELTA > datetime.now():
                raise ValidationError(_('The selected year and month must start in the past.'))


    def _validate_state(self, states=[0]):
        ''' Validates that all the records in the 'records' recordset have the state number from 'states' (int or list of ints) of STATES '''
        if isinstance(states, int):
            states = [states]
        for record in self:
            state_strings = [STATES[state][0] for state in states]
            state_names = ', '.join([STATES[state][1] for state in states])
            if record.state not in state_strings:
                raise ValidationError(_('This operation can only be done in the %s state(s).') % state_names)


    def _validate_product_categories(self):
        errors = []
        if not self.company_id.cogs_report_category_raw_id:
            errors.append(_('Product Category for Raw Material'))
        if not self.company_id.cogs_report_category_sub_id:
            errors.append(_('Product Category for Sub Material'))

        if errors:
            missing_category_lines = '\n'.join(errors)
            raise ValidationError(_("This operation cannot be processed because necessary Product Categories are not selected in Accounting Settings - COGS Reports Product Categories.") + '\n\n' + _("Missing categories:") + '\n' + missing_category_lines)


    # def _allocation_domain(self):
    #     domain = []
    #     year = self.year or self._default_year
    #     month = self.month or self._default_month
    #     domain += [('year', '=', year)]
    #     domain += [('month', '=', month)]
    #     domain += [('state', '=', 'done')]
    #     return domain


    def ensure_one_names(self):
        try:
            self.ensure_one()
        except:
            record_names = [r.name_get()[0][1] for r in self]
            record_names_string = "\n".join(record_names)
            raise ValidationError(_("Only one record can be processed at a time. Records you tried to process:\n\n%s") % record_names_string)


    _default_year = lambda l: str((datetime.now()+TIMEZONE_RELATIVEDELTA).year)
    _default_month = lambda l: str((datetime.now()+TIMEZONE_RELATIVEDELTA).month)

    state = fields.Selection(STATES, default=DEFAULT_STATE, copy=False)
    summary_line_ids = fields.One2many('cogs.report.summary.line', 'cogs_report_id',
        'COGS Summary Lines', copy=False)
    material_loss_id = fields.Many2one('lp_cost_recalculation.material.loss.allocation',
        'Material Loss Allocation', required=True, copy=False)
    labor_cost_id = fields.Many2one('lp_cost_recalculation.labor.cost.allocation',
        'Labor Cost Allocation', required=True, copy=False)
    click_charge_id = fields.Many2one('lp_cost_recalculation.click.charge.allocation',
        'Click Charge Allocation', required=True, copy=False)
    overhead_cost_id = fields.Many2one('lp_cost_recalculation.overhead.cost.allocation',
        'Overhead Cost Allocation', required=True, copy=False)
    year = fields.Selection(_get_available_years, default=_default_year)
    month = fields.Selection(MONTHS, default=_default_month)
    name = fields.Char(required=True)
    date_from = fields.Datetime(compute='_compute_dates_file_names', store=True)
    date_to = fields.Datetime(compute='_compute_dates_file_names', store=True)
    company_id = fields.Many2one('res.company', 'Company', related='material_loss_id.company_id')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.company.currency_id.id)
    cogs_pack_xlsx = fields.Binary('COGS Pack XLSX Report', readonly=True, copy=False)
    cogs_pack_xlsx_filename = fields.Char('COGS Pack XLSX Report Filename', compute='_compute_dates_file_names')
    cogs_summary_xlsx = fields.Binary('COGS Summary Report XLSX', readonly=True, copy=False)
    cogs_summary_xlsx_filename = fields.Char('COGS Summary Report XLSX Filename', compute='_compute_dates_file_names')


    @api.depends('year', 'month')
    def _compute_dates_file_names(self):
        name_pack = _(' - COGS Pack Report')
        name_summary = _(' - COGS Summary Report')
        for record in self:
            if record.year and record.month:
                # Compute dates
                date_from = datetime(int(record.year), int(record.month), 1)
                date_to = date_from + relativedelta(months=1) - relativedelta(seconds=1)
                if date_from > datetime.now():
                    raise ValidationError(_("You can't select a month that hasn't started yet."))
                date_from = date_from - TIMEZONE_RELATIVEDELTA
                date_to = date_to - TIMEZONE_RELATIVEDELTA
                if not record.name:
                    # Set name if empty
                    record.name = _("COGS Report %s/%s") % (record.year, record.month)
                # Compute file names
                report_datetime = '%s/%02d' % (record.year, int(record.month))
                filename_pack = slugify(report_datetime + name_pack) + '.xlsx'
                filename_summary = slugify(report_datetime + name_summary) + '.xlsx'
            else:
                # If year and month not selected
                date_from = date_to = False
                filename_pack = filename_summary = 'report.xlsx'
            # Set dates
            record.date_from = date_from
            record.date_to = date_to
            # Set filenames
            record.cogs_pack_xlsx_filename = filename_pack
            record.cogs_summary_xlsx_filename = filename_summary


    # @api.depends('year', 'month')
    # def _compute_xlsx_names(self):
    #     name_pack = _(' - COGS Pack Report')
    #     name_summary = _(' - COGS Summary Report')
    #     for record in self:
    #         if record.year and record.month:
    #             report_datetime = '%s/%02d' % (record.year, int(record.month))
    #             filename_pack = slugify(report_datetime + name_pack) + '.xlsx'
    #             filename_summary = slugify(report_datetime + name_summary) + '.xlsx'
    #         else:
    #             filename_pack = filename_summary = 'report.xlsx'
    #         record.cogs_pack_xlsx_filename = filename_pack
    #         record.cogs_summary_xlsx_filename = filename_summary


    def button_draft(self):
        self._validate_state(1)
        self.write({
            'summary_line_ids': (5, 0, 0),
            'state': STATES[0][0],
            'cogs_pack_xlsx': False,
            'cogs_summary_xlsx': False,
        })


    def button_compute_reports(self):
        self.ensure_one_names()
        self._validate_state(0)
        self._validate_dates()
        self._validate_product_categories()
        self.write({
            'summary_line_ids': (5, 0, 0),
            'state': STATES[1][0],
            'cogs_pack_xlsx': False,
            'cogs_summary_xlsx': False,
        })



class SummaryLine(models.Model):
    _name = 'cogs.report.summary.line'
    _description = 'COGS Report Summary Line'

    cogs_report_id = fields.Many2one('cogs.report', 'Parent COGS Report')
    currency_id = fields.Many2one(related='cogs_report_id.currency_id')
    product_id = fields.Many2one('product.product', 'Product')
    product_code = fields.Char(related='product_id.default_code')
    product_name = fields.Char(related='product_id.name')
    lpus_category_id = fields.Many2one('product.category', 'LPUS Category', related='product_id.') # TODO categ_id? see comment in FRD
    uom_id = fields.Many2one('uom.uom', 'Unit', related='product_id.uom_id')
    initial_quantity = fields.Integer()
    initial_bom_raw_material = fields.Monetary('1541C – BOM Raw Material (Initial)')
    initial_bom_sub_material = fields.Monetary('1541P – BOM Sub Material (Initial)')
    initial_direct_labor = fields.Monetary('622 – Direct Labor (Initial)')
    initial_printing_cost = fields.Monetary('1543P – Printing Cost (Initial)')
    initial_general_production_cost = fields.Monetary('627 – General Production Cost (Initial)')
    initial_finished_goods = fields.Integer('Finished Goods (Initial)')
    quantity = fields.Integer()
    ceq_quantity = fields.Float('CEQ Quantity', compute='_compute_values')
    bom_raw_material = fields.Monetary('1541C – BOM Raw Material')
    bom_sub_material = fields.Monetary('1541P – BOM Sub Material')
    material_loss_allocation = fields.Monetary('Material Loss Allocation')
    direct_labor = fields.Monetary('622 – Direct Labor')
    labor_cost_allocation = fields.Monetary('Labor Cost Allocation')
    printing_cost = fields.Monetary('1543P – Printing Cost')
    printing_cost_allocation = fields.Monetary('Printing Cost Allocation')
    general_production_cost = fields.Monetary('627 – General Production Cost')
    production_in_month = fields.Monetary('Production in Month')
    sold_quantity = fields.Integer()
    ceq_sold_quantity = fields.Float('CEQ Sold Quantity')
    unit_cost = fields.Monetary()
    cogs = fields.Monetary('COGS')
    detail_raw_material = fields.Monetary('1541C – Raw Material (Detail)')
    detail_sub_material = fields.Monetary('1541P – Sub Material (Detail)')
    detail_direct_labor = fields.Monetary('622 – Direct Labor (Detail)')
    detail_printing_cost = fields.Monetary('1543P – Printing Cost (Detail)')
    detail_general_production_cost = fields.Monetary('627 – General Production Cost (Detail)')
    ending_raw_material = fields.Monetary('1541C – Raw Material (Ending)')
    ending_sub_material = fields.Monetary('1541P – Sub Material (Ending)')
    ending_direct_labor = fields.Monetary('622 – Direct Labor (Ending)')
    ending_printing_cost = fields.Monetary('1543P – Printing Cost (Ending)')
    ending_general_production_cost = fields.Monetary('627 – General Production Cost (Ending)')
    ending_cogs = fields.Monetary('COGS (Ending)')


    @api.depends('', '')
    def _compute_values(self):
        a = 1



# class MaterialLossConsumedLine(models.Model):
#     _name = 'lp_cost_recalculation.material.loss.consumed.line'
#     _description = 'List LP Consumed Material Loss: lines for computing consumed material loss allocation'
#     _inherit = 'lp_cost_recalculation.abstract.allocation.line'

#     material_id = fields.Many2one('product.product', 'Material')
#     ceq_factor = fields.Float('CEQ Factor')
#     ceq_converted_qty = fields.Float('CEQ Converted Quantity')
#     material_loss_allocation = fields.Float(digits=(32,4))
#     material_loss_allocation_id = fields.Many2one('lp_cost_recalculation.material.loss.allocation', 'Parent Material Loss Allocation')
#     delta_line_id = fields.Many2one('lp_cost_recalculation.material.loss.line', 'Origin Material Loss Line')
#     currency_id = fields.Many2one('res.currency', string='Currency', related='material_loss_allocation_id.currency_id')
