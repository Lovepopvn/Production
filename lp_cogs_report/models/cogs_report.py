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

STATES = [('draft', 'Draft'), ('calculated', 'Calculated'), ('locked', 'Locked')]
DEFAULT_STATE = STATES[0][0]

ALLOCATION_DOMAIN = "[('date_from', '=', date_from), ('date_to', '=', date_to), "\
     + "('company_id', '=', company_id), ('state', '=', 'posted')]"

PREVIOUS_REPORT_DOMAIN = "[('date_from', '=', previous_date_from), "\
     + "('date_to', '=', previous_date_to), ('state', '=', '%s')]" % (STATES[2][0])

DATE_FORMAT = _('%d/%m/%Y')
EXCEL_DATE_FORMAT = _('dd/mm/yyyy')

EXCEL_FONT_SIZE = 10
EXCEL_FONT = 'Arial'

PACK_TOP_HEADERS = [
    {
        'start': 0,
        'end': 4,
        'background': False,
        'background_header': '#34a853',
        'text': '',
    },
    {
        'start': 5,
        'end': 14,
        'background': '#f7caac',
        'background_header': '#92d050',
        'text': _('FINISHED GOODS'),
    },
]
PACK_HEADERS = [
    ('mo', _('MO Number')),
    ('product', _('Product')),
    ('product_code', _('Internal Reference')),
    ('product_name', _('Product Name')),
    ('parent_mo', _('Parent MO')),
    ('quantity', _('Quantity')),
    ('raw_material', _('1541C\nBOM Raw Material')),
    ('sub_material', _('1541P\nBOM Sub Material')),
    ('material_loss_allocation', _('Material Loss Allocation'), '#00ffff'), # TODO color?
    ('printing_cost', _('1543P\nPrinting Cost')),
    ('printing_allocation', _('Printing Allocation'), '#00ffff'),
    ('direct_labor', _('622\nDirect Labor')),
    ('direct_labor_allocation', _('Direct Labor Allocation'), '#00ffff'),
    ('production_cost', _('627\nGeneral Production Cost')),
    ('total_value', _('Finished Goods Total Value')),
]

SUMMARY_TOP_HEADERS = [
    {
        'start': 0,
        'end': 4,
        'background': False,
        'background_header': '#92d050',
        'text': '',
    },
    {
        'start': 5,
        'end': 11,
        'background': '#f7caac',
        'background_header': '#fce5cd',
        'text': _('Beginning'),
    },
    {
        'start': 12,
        'end': 22,
        'background': '#a4c2f4',
        'background_header': '#a4c2f4',
        'text': _('FINISHED GOODS'),
    },
    {
        'start': 23,
        'end': 31,
        'background': '#dd7e6b',
        'background_header': '#ea9999',
        'text': _('DETAIL COGS'),
    },
    {
        'start': 32,
        'end': 38,
        'background': '#b6d7a8',
        'background_header': '#92d050',
        'text': _('Ending Value / Inventory Value'),
    },
]
SUMMARY_COLUMNS = [
    'product_id',
    'product_code',
    'product_name',
    'lpus_category_id',
    'uom_id',
    'initial_quantity',
    'initial_bom_raw_material',
    'initial_bom_sub_material',
    'initial_direct_labor',
    'initial_printing_cost',
    'initial_general_production_cost',
    'initial_finished_goods',
    'quantity',
    'ceq_quantity',
    'bom_raw_material',
    'bom_sub_material',
    'material_loss_allocation',
    'direct_labor',
    'labor_cost_allocation',
    'printing_cost',
    'printing_cost_allocation',
    'general_production_cost',
    'production_in_month',
    'sold_quantity',
    'ceq_sold_quantity',
    'unit_cost',
    'cogs',
    'detail_raw_material',
    'detail_sub_material',
    'detail_direct_labor',
    'detail_printing_cost',
    'detail_general_production_cost',
    'ending_quantity',
    'ending_raw_material',
    'ending_sub_material',
    'ending_direct_labor',
    'ending_printing_cost',
    'ending_general_production_cost',
    'ending_finished_goods',
]


class COGSReport(models.Model):
    _name = 'cogs.report'
    _description = 'COGS Report'
    _order = 'date_to desc, id desc'


    @api.model
    def _get_available_years(self, initial_year=2020):
        ''' Returns years available for reporting (from initial_year to now) 
        in a list of (str, str) tuples '''
        now = datetime.now() + TIMEZONE_RELATIVEDELTA
        current_year = now.year
        available_years_int = list(range(initial_year, current_year + 1))
        available_years = [(str(year), str(year)) for year in available_years_int]
        return available_years


    def _validate_dates(self):
        ''' Validates that dates of the report are selected and start in the past '''
        for record in self:
            if not record.date_from or not record.date_to:
                raise ValidationError(_('You must select the year and month to calculate the data for.'))
            if record.date_from + TIMEZONE_RELATIVEDELTA > datetime.now():
                raise ValidationError(_('The selected year and month must start in the past.'))


    def _validate_allocations(self):
        ''' Validates that the selected allocations are in the Posted state '''
        errors = {
            'states': [],
            'companies': [],
        }
        for record in self:
            companies = []
            for allocation in ('material_loss_id', 'labor_cost_id', 'click_charge_id', 'overhead_cost_id'):
                if record[allocation] and record[allocation].state != 'posted':
                    errors['states'].append(record[allocation].name_get()[0][1])
                if record[allocation] and record[allocation].company_id \
                    and record[allocation].company_id.id != record.company_id.id:
                    companies.append((record[allocation].name_get()[0][1], record[allocation].company_id.name_get()[0][1]))
            if companies:
                errors['companies'].append((record.name_get()[0][1], record.company_id.name_get()[0][1], companies))
        error_msg = ''
        if errors['states']:
            wrong_allocations = '\n'.join(errors['states'])
            error_msg += _('Allocations not in Posted state:') + '\n\n' + wrong_allocations + '\n\n'
        for error in errors['companies']:
            wrong_allocations = '\n'.join(['%s (%s)' % e for e in error[2]])
            error_msg += _('Allocations must belong to the same company as this report.') \
                + '\n\n' + _('Report "%s" (company "%s"):') % (error[0], error[1]) + '\n' \
                + _('Allocations belonging to different companies:') \
                + '\n' + wrong_allocations
        if error_msg:
            raise ValidationError(error_msg)


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
        ''' Validates that the product categories for COGS report are filled in Settings '''
        errors = []
        if not self.company_id.cogs_report_category_finished_id:
            errors.append(_('Product Category for Finished Goods'))
        if not self.company_id.cogs_report_category_pack_id:
            errors.append(_('LPUS Product Category for Packs'))
        if not self.company_id.cogs_report_category_raw_id:
            errors.append(_('Product Category for Raw Materials'))
        if not self.company_id.cogs_report_category_sub_id:
            errors.append(_('Product Category for Sub Materials'))

        if errors:
            missing_category_lines = '\n'.join(errors)
            raise ValidationError(_("This operation cannot be processed because necessary Product Categories are not selected in Accounting Settings – COGS Reports Product Categories.") + '\n\n' + _("Missing categories:") + '\n' + missing_category_lines)


    @api.model
    def _validate_products_categories(self, products):
        ''' Validates that the products in provided recordset all have lpus_category_id '''
        errors = []

        for product in products:
            if not product.lpus_category_id:
                errors += [product.name_get()[0][1]]

        if errors:
            missing_products = '\n'.join(errors)
            raise ValidationError(_("This operation cannot be processed because the LPUS Category"
                + " is not set on these products:") + '\n\n' + missing_products)


    def ensure_one_names(self):
        ''' Validates that only a single record is being processed. If not, lists their names. '''
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
        'Material Loss Allocation', copy=False, domain=ALLOCATION_DOMAIN)
    labor_cost_id = fields.Many2one('lp_cost_recalculation.labor.cost.allocation',
        'Labor Cost Allocation', copy=False, domain=ALLOCATION_DOMAIN)
    click_charge_id = fields.Many2one('lp_cost_recalculation.click.charge.allocation',
        'Click Charge Allocation', copy=False, domain=ALLOCATION_DOMAIN)
    overhead_cost_id = fields.Many2one('lp_cost_recalculation.overhead.cost.allocation',
        'Overhead Cost Allocation', copy=False, domain=ALLOCATION_DOMAIN)
    previous_report_id = fields.Many2one('cogs.report', "Previous Month's Report", copy=False,
        domain=PREVIOUS_REPORT_DOMAIN)
    year = fields.Selection(_get_available_years, default=_default_year)
    month = fields.Selection(MONTHS, default=_default_month)
    name = fields.Char(required=True)
    date_from = fields.Datetime(compute='_compute_dates_file_name', store=True)
    date_to = fields.Datetime(compute='_compute_dates_file_name', store=True)
    previous_date_from = fields.Datetime(compute='_compute_dates_file_name', store=True)
    previous_date_to = fields.Datetime(compute='_compute_dates_file_name', store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company,
        required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.company.currency_id.id)
    cogs_report_xlsx = fields.Binary('COGS Report XLSX', readonly=True, copy=False)
    cogs_xlsx_filename = fields.Char('COGS Report XLSX Filename', compute='_compute_dates_file_name', store=True)


    @api.depends('year', 'month')
    def _compute_dates_file_name(self):
        ''' Computes dates of current report, previous report (for its domain),
        and a file name for the generated XLSX report '''
        name = _(' – COGS Report')
        for record in self:
            if record.year and record.month:
                # Compute dates
                delta_month = relativedelta(months=1)
                delta_second = relativedelta(seconds=1)
                date_from = datetime(int(record.year), int(record.month), 1)
                date_to = date_from + delta_month - delta_second
                if date_from > datetime.now():
                    raise ValidationError(_("You can't select a month that hasn't started yet."))
                previous_date_from = date_from - delta_month
                previous_date_to = previous_date_from + delta_month - delta_second
                date_from -= TIMEZONE_RELATIVEDELTA
                date_to -= TIMEZONE_RELATIVEDELTA
                previous_date_from -= TIMEZONE_RELATIVEDELTA
                previous_date_to -= TIMEZONE_RELATIVEDELTA
                # Set name and empty previous report
                report_datetime = '%s/%02d' % (record.year, int(record.month))
                record.name = _("COGS Report %s") % report_datetime
                record.previous_report_id = False
                # Compute file names
                filename = slugify(report_datetime + name) + '.xlsx'
            else:
                # If year and month not selected
                date_from = date_to = previous_date_from = previous_date_to = False
                filename = 'report.xlsx'
            # Set dates
            record.date_from = date_from
            record.date_to = date_to
            record.previous_date_from = previous_date_from
            record.previous_date_to = previous_date_to
            # Set filenames
            record.cogs_xlsx_filename = filename


    def unlink(self):
        ''' Overrides default unlink() and validates that the report is not in the second state '''
        for report in self:
            if report.state == STATES[2][0]:
                raise UserError(_('You cannot delete a document that is in %s state.') % STATES[2][1])
        return super(COGSReport, self).unlink()


    def button_draft(self):
        ''' Moves report to Draft state and deletes lines and XLSX report '''
        self._validate_state(1)
        self.write({
            'summary_line_ids': [(5, 0, 0)],
            'state': STATES[0][0],
            'cogs_report_xlsx': False,
        })


    def button_lock(self):
        ''' Moves report to the Locked state '''
        self._validate_state(1)
        self.write({
            'state': STATES[2][0],
        })


    def button_compute_reports(self):
        ''' Computes reports' data and moves report to Calculated state '''
        self.ensure_one_names()
        self._validate_state(0)
        self._validate_dates()
        self._validate_product_categories()
        self._validate_allocations()

        pack_report_data = self._get_pack_report_data()
        self._compute_summary(pack_report_data)

        summary_headers, summary_report_data = self._get_summary_lines_data()
        self._create_xlsx_report(PACK_HEADERS, PACK_TOP_HEADERS, pack_report_data,
            summary_headers, SUMMARY_TOP_HEADERS, summary_report_data)

        self.write({
            'state': STATES[1][0],
        })


    def _compute_summary(self, pack_report_data):
        ''' Computes summary lines of the report using provided Pack and WIP Pack data '''
        self.ensure_one_names()
        MO = self.env['mrp.production']

        current_mos = MO.search([
            ('state', '=', 'done'),
            ('date_finished', '>=', self.date_from),
            ('date_finished', '<=', self.date_to),
            ('parent_mo_id', '=', False),
        ])

        products = current_mos.mapped('product_id')
        if self.previous_report_id:
            products += self.previous_report_id.summary_line_ids.mapped('product_id')
        self._validate_products_categories(products)

        lines = []
        for product in products:
            mos = current_mos.filtered(lambda m: m.product_id.id == product.id)
            line_vals = self._get_summary_line_vals(product, mos, pack_report_data)
            lines.append((0, 0, line_vals))
        self.write({'summary_line_ids': lines})
        self.summary_line_ids._compute_values()


    def _get_summary_line_vals(self, product, mos, pack_report_data):
        ''' Prepares values for summary line from provided Product '''
        self.ensure_one_names()
        self._validate_product_categories()

        pack_id = self.company_id.cogs_report_category_pack_id.id
        raw_material_id = self.company_id.cogs_report_category_raw_id.id
        sub_material_id = self.company_id.cogs_report_category_sub_id.id

        quantity = sum(mos.filtered(lambda m: not m.parent_mo_id).finished_move_line_ids.mapped('qty_done'))

        pack_lines_product = [line for line in pack_report_data['lines_pack']
            if line['product'].id == product.id]
        # wip_lines_product = {line['mo'].id: line for line in pack_report_data['lines_wip_pack']
        #     if line['product'].id == product.id}

        bom_raw_material = bom_sub_material = material_loss_allocation = direct_labor = \
            labor_cost_allocation = printing_cost = printing_cost_allocation = \
            general_production_cost = sold_quantity = 0
        if product.lpus_category_id.id != pack_id:
            bom_raw_material = self._get_cost_of_components(mos, raw_material_id)
            bom_sub_material = self._get_cost_of_components(mos, sub_material_id)
            material_loss_allocation = self._get_allocation_rounding(self.material_loss_id, product)
            direct_labor = self._get_cost_of_operations(mos)
            labor_cost_allocation = self._get_allocation_rounding(self.labor_cost_id, product)
            printing_cost = self._get_cost_of_printing(mos)
            printing_cost_allocation = self._get_allocation_rounding(self.click_charge_id, product)
            general_production_cost = self._get_allocation_rounding(self.overhead_cost_id, product)
        else:
            bom_raw_material = sum([l['raw_material'] for l in pack_lines_product])
            bom_sub_material = sum([l['sub_material'] for l in pack_lines_product])
            material_loss_allocation = sum([l['material_loss_allocation'] for l in pack_lines_product])
            direct_labor = sum([l['direct_labor'] for l in pack_lines_product])
            labor_cost_allocation = sum([l['direct_labor_allocation'] for l in pack_lines_product])
            printing_cost = sum([l['printing_cost'] for l in pack_lines_product])
            printing_cost_allocation = sum([l['printing_allocation'] for l in pack_lines_product])
            general_production_cost = sum([l['production_cost'] for l in pack_lines_product])
        mos_sold = mos.filtered(lambda m: m.product_lot_ids 
            and m.product_lot_ids[0].delivery_order_id.state == 'done' 
            and m.product_lot_ids[0].delivery_order_id.date_done >= self.date_from
            and m.product_lot_ids[0].delivery_order_id.date_done >= self.date_to)
        sold_quantity = sum(mos_sold.finished_move_line_ids.mapped('qty_done'))

        line_vals = {
            'product_id': product.id,
            'quantity': quantity,
            'bom_raw_material': bom_raw_material,
            'bom_sub_material': bom_sub_material,
            'material_loss_allocation': material_loss_allocation,
            'direct_labor': direct_labor,
            'labor_cost_allocation': labor_cost_allocation,
            'printing_cost': printing_cost,
            'printing_cost_allocation': printing_cost_allocation,
            'general_production_cost': general_production_cost,
            'sold_quantity': sold_quantity,
        }
        return line_vals



    def _get_summary_lines_data(self):
        ''' Computes headers and data for the Summary sheet of XLSX export from report lines '''
        self.ensure_one_names()

        fields = self.summary_line_ids.fields_get()
        headers = [(field, fields[field]['string']) for field in SUMMARY_COLUMNS]

        lines_values = []
        for line in self.summary_line_ids:
            line_values = {}
            for field in SUMMARY_COLUMNS:
                field_content = line[field]
                if field[-3:] == '_id':
                    if len(field_content) > 0:
                        line_values[field] = field_content.name_get()[0][1]
                    else:
                        line_values.append[field] = ''
                elif isinstance(field_content, (int, float)):
                    line_values[field] = field_content
                else:
                    line_values[field] = str(field_content)
            lines_values += [line_values]

        return headers, lines_values


    def _create_xlsx_report(self, headers, top_headers, data, sum_headers, sum_top_headers, sum_data):
        ''' Creates a three-sheet XLSX workbook from provided data and saves it to the report. '''
        self.ensure_one_names()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Define workbook styles
        default_style = {'font_size': EXCEL_FONT_SIZE, 'font_name': EXCEL_FONT}
        style_header_values = dict(default_style)
        style_header_values.update({'bold': True, 'bg_color': '#eeeeee', 'text_wrap': True})
        style_data_values = dict(default_style)
        style_data_values.update({'num_format': '#,##0.0000'})
        style_report_name_values = dict(style_data_values)
        style_report_name_values.update({'font_size': 16, 'align': 'center', 'valign': 'vcenter', 
            'bold': True})

        style_header = workbook.add_format(style_header_values)
        style_header.set_text_wrap()
        style_report_name = workbook.add_format(style_report_name_values)
        style_data = workbook.add_format(style_data_values)

        # pack sheets
        type_pack = _('Pack Product')
        sheet_pack = workbook.add_worksheet(_('COGS Pack'))
        type_wip = _('WIP Pack Product')
        sheet_wip = workbook.add_worksheet(_('COGS WIP Pack'))

        styles = {
            'report_name': style_report_name,
            'header': style_header,
            'data': style_data,
            'header_values': style_header_values,
            'data_values': style_data_values,
            'top_headers': PACK_TOP_HEADERS,
            'header_styles': {},
        }
        self._write_sheet(workbook, sheet_pack, headers, data['lines_pack'], styles, type_pack)
        self._write_sheet(workbook, sheet_wip, headers, data['lines_wip_pack'], styles, type_wip)

        # summary sheet
        type_summary = _('Summary')
        sheet_summary = workbook.add_worksheet(_('COGS Summary'))
        styles['top_headers'] = SUMMARY_TOP_HEADERS
        self._write_sheet(workbook, sheet_summary, sum_headers, sum_data, styles, type_summary)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        self.write({'cogs_report_xlsx': base64.encodebytes(generated_file)})


    def _write_sheet(self, workbook, sheet, headers, lines, styles, report_type):
        ''' Writes provided data to provided sheets of a provided worksheet. '''
        self.ensure_one_names()

        # Set column width
        sheet.set_column(0, len(headers) - 1, 25)
        # sheet.set_column(0, 1, 30)
        # sheet.set_column(2, len(headers) - 1, 27)
        # Set row height
        sheet.set_row(2, 20)
        sheet.set_row(6, 24)

        # Prepare sheet headers
        company = self.company_id
        company_name = company.name
        company_address = ', '.join([str(i) for i in [
            company.street,
            company.street2,
            company.city,
            company.state_id.name,
            company.zip,
            company.country_id.name
        ] if i])
        report_name = _('COST OF GOODS SOLD – %s') % report_type
        report_period_label = _('Report period')
        report_period = _('From %s to %s') % (
            (self.date_from + TIMEZONE_RELATIVEDELTA).strftime(DATE_FORMAT),
            (self.date_to + TIMEZONE_RELATIVEDELTA).strftime(DATE_FORMAT)
        )

        # Write sheet headers
        sheet.merge_range('A1:E1', company_name, styles['data'])
        sheet.merge_range('A2:E2', company_address, styles['data'])
        sheet.merge_range('A3:E3', report_name, styles['report_name'])
        sheet.write('A4', report_period_label, styles['data'])
        sheet.merge_range('B4:C4', report_period, styles['data'])

        # Prepare top data headers
        offset_y = 5
        for top_header in styles['top_headers']:
            style_values = dict(styles['header_values'])
            style_values.update({'bg_color': top_header['background'], 'align': 'center'})
            style = workbook.add_format(style_values)
            sheet.merge_range(offset_y, top_header['start'], offset_y, top_header['end'],
                top_header['text'], style)
            style_header_values = dict(styles['header_values'])
            style_header_values.update({'bg_color': top_header['background_header']})
            style_header = workbook.add_format(style_header_values)
            for x in range(top_header['start'], top_header['end'] + 1):
                styles['header_styles'][x] = style_header

        # Write data headers
        offset_x = 0
        offset_y += 1
        for header in headers:
            style = styles['header']
            if offset_x in styles['header_styles']:
                style = styles['header_styles'][offset_x]
            sheet.write(offset_y, offset_x, header[1], style)
            offset_x += 1

        # Write data
        for line in lines:
            offset_y += 1
            offset_x = 0
            for header in headers:
                value = line[header[0]]
                if type(value) not in (int, str, float):
                    # probably a record(set)
                    try:
                        value = value.name_get()[0][1]
                    except:
                        # value = str(value)
                        value = ''
                    if not value:
                        value = ''
                sheet.write(offset_y, offset_x, value, styles['data'])
                offset_x += 1
        return offset_y


    def _get_pack_report_data(self):
        ''' Computes data for Pack and WIP Pack report. Returns dict with lists of dicts as lines. '''
        self.ensure_one_names()
        self._validate_dates()
        self._validate_product_categories()

        _mo_sort = lambda l: str((l.parent_mo_id and l.parent_mo_id.name or '') + (l.name or ''))

        finished_goods_id = self.company_id.cogs_report_category_finished_id.id
        pack_id = self.company_id.cogs_report_category_pack_id.id
        sub_material_id = self.company_id.cogs_report_category_sub_id.id
        Product = self.env['product.product']
        MO = self.env['mrp.production']

        # Get IDs of all Pack products (→ their MOs are always parent MOs)
        finished_pack_products_ids = Product.search([('categ_id.id', '=', finished_goods_id),
            ('lpus_category_id.id', '=', pack_id)]).ids

        # Find done pack MOs in period (Pack report)
        mos_pack_products = MO.search([
            ('product_id', 'in', finished_pack_products_ids),
            ('state', '=', 'done'),
            ('date_finished', '>=', self.date_from),
            ('date_finished', '<=', self.date_to),
        ])
        # Find their child MOs done in period
        mos_pack_sub = MO.search([
            ('parent_mo_id', 'in', mos_pack_products.ids),
            ('state', '=', 'done'),
            ('date_finished', '>=', self.date_from),
            ('date_finished', '<=', self.date_to),
        ])
        # Concatenate the lists to have both parent and child MOs in one list
        mos_pack = (mos_pack_products + mos_pack_sub).sorted(key=_mo_sort)
        # Find unfinished pack MOs (WIP Pack report)
        mos_wip_products = MO.search([
            ('product_id', 'in', finished_pack_products_ids),
            ('state', 'not in', ('done', 'cancel')),
            ('create_date', '>=', self.date_from),
            ('create_date', '<=', self.date_to),
        ])
        # Find their child MOs done in period
        mos_wip_sub = MO.search([
            ('parent_mo_id', 'in', mos_wip_products.ids),
            ('state', '=', 'done'),
            ('date_finished', '>=', self.date_from),
            ('date_finished', '<=', self.date_to),
        ])
        # Filter out parent MOs with no child MOs done within the period
        mos_wip_products = mos_wip_products.filtered(lambda m: m.id in mos_wip_sub.parent_mo_id.ids)
        # Concatenate the lists to have both parent and child MOs in one list
        mos_wip = (mos_wip_products + mos_wip_sub).sorted(key=_mo_sort)

        data = {
            'lines_pack': self._get_report_lines(mos_pack),
            'lines_wip_pack': self._get_report_lines(mos_wip, True),
        }
        return data

    def _get_report_lines(self, mos, wip=False):
        ''' Computes lines for Pack and WIP Pack reports. Returns list of dicts. '''
        self.ensure_one_names()
        self._validate_product_categories()
        raw_material_id = self.company_id.cogs_report_category_raw_id.id
        sub_material_id = self.company_id.cogs_report_category_sub_id.id
        lines = {}
        for mo in mos:
            parent_mo = mo.parent_mo_id
            product = mo.product_id
            if parent_mo and parent_mo.id not in mos.ids:
                continue
            quantity = sum(mo.finished_move_line_ids.mapped('qty_done'))
            raw_material = sub_material = printing_cost = direct_labor = 0
            if parent_mo or not wip:
                raw_material = self._get_cost_of_components(mo, raw_material_id)
                sub_material = self._get_cost_of_components(mo, sub_material_id)
                printing_cost = self._get_cost_of_printing(mo)
                direct_labor = self._get_cost_of_operations(mo)
            material_loss_allocation = 0

            lines[mo.id] = {
                'mo': mo,
                'product': product,
                'product_code': product.default_code,
                'product_name': product.name,
                'parent_mo': parent_mo,
                'quantity': quantity,
                'raw_material': raw_material,
                'sub_material': sub_material,
                'material_loss_allocation': 0,
                'printing_cost': printing_cost,
                'printing_allocation': 0,
                'direct_labor': direct_labor,
                'direct_labor_allocation': 0,
                'production_cost': 0,
                'total_value': False,
            }
        lines = self._process_report_lines(lines, wip)
        return list(lines.values())


    def _process_report_lines(self, lines, wip=False):
        ''' Processes provided list of dicts (lines) to add/update values that need the rest of the lines to have already been created. '''
        self.ensure_one_names()
        for mo_id, line in lines.items():
            if not line['parent_mo']:
                raw_material = sub_material = printing_cost = direct_labor = 0
                lines_filtered = [
                    (l['raw_material'], l['sub_material'], l['printing_cost'], l['direct_labor'])
                    for l in lines.values()
                    if l['parent_mo'] and l['parent_mo'].id == mo_id
                ]
                if lines_filtered:
                    # transpose [(raw1, sub1, printing1, direct1), (raw2, sub2, printing2, direct2)]
                    # into [(raw1, raw2), (sub1, sub2), (printing1, printing2), (direct1, direct2)]
                    costs = zip(*lines_filtered)
                    # ...and sum each group
                    raw_material, sub_material, printing_cost, direct_labor = (sum(c) for c in costs)

                material_loss_allocation = printing_allocation = direct_labor_allocation = \
                    production_cost = 0
                quantity_sum = sum(
                    l['quantity'] for l in lines.values() if l['product'].id == line['product'].id)
                if quantity_sum:
                    product_id = line['product'].id
                    quantity = line['quantity']

                    material_loss_allocation = self._get_allocation_value(
                        self.material_loss_id, product_id, mo_id, quantity_sum, quantity, wip)
                    printing_allocation = self._get_allocation_value(
                        self.click_charge_id, product_id, mo_id, quantity_sum, quantity, wip)
                    direct_labor_allocation = self._get_allocation_value(
                        self.labor_cost_id, product_id, mo_id, quantity_sum, quantity, wip)
                    production_cost = self._get_allocation_value(
                        self.overhead_cost_id, product_id, mo_id, quantity_sum, quantity, wip)

                line.update({
                    'raw_material': raw_material + line['raw_material'],
                    'sub_material': sub_material + line['sub_material'],
                    'printing_cost': printing_cost + line['printing_cost'],
                    'direct_labor': direct_labor + line['direct_labor'],
                    'material_loss_allocation': round(material_loss_allocation),
                    'printing_allocation': round(printing_allocation),
                    'direct_labor_allocation': round(direct_labor_allocation),
                    'production_cost': round(production_cost),
                })
            total_value = line['raw_material'] + line['sub_material'] \
                + line['material_loss_allocation'] + line['printing_cost'] \
                + line['printing_allocation'] + line['direct_labor'] \
                + line['direct_labor_allocation'] + line['production_cost']
            line['total_value'] = total_value
            lines[mo_id] = line
        return lines


    @api.model
    def _get_cost_of_components(self, mos, category_id):
        ''' Retrieves total cost of components of provided MOs. '''
        # copied and adjusted from mrp_account_enterprise/reports/mrp_cost_structure.py:17
        total_cost = 0.0

        if mos:
            #get the cost of raw material effectively used
            query_str = """SELECT sm.product_id, abs(SUM(svl.value))
                FROM stock_move AS sm
                    LEFT JOIN product_product AS pp ON pp.id = sm.product_id
                    LEFT JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
                    INNER JOIN stock_valuation_layer AS svl ON svl.stock_move_id = sm.id
                WHERE sm.raw_material_production_id in %s
                    AND sm.state != 'cancel'
                    AND sm.product_qty != 0
                    AND scrapped != 't'
                    AND pt.categ_id = %s
                GROUP BY sm.bom_line_id, sm.product_id"""
            self.env.cr.execute(query_str, (tuple(mos.ids), category_id))
            for product_id, cost in self.env.cr.fetchall():
                total_cost += cost
        return total_cost


    @api.model
    def _get_cost_of_printing(self, mos):
        ''' Retrieves total cost of printing of provided MOs. '''
        cost = 0.0
        if mos:
            sides = sum(mos.follower_sheets_ids.mapped('total_printed_side'))
            cost = sides * sum(mos.mapped('average_printing_cost_when_done'))
        return cost


    @api.model
    def _get_cost_of_operations(self, mos):
        ''' Retrieves total cost of operations of provided MOs. '''
        # copied and adjusted from mrp_account_enterprise/reports/mrp_cost_structure.py:17
        total_cost = 0.0

        #get the cost of operations
        if mos:
            Workorders = self.env['mrp.workorder'].search([('production_id', 'in', mos.ids)])
            if Workorders:
                query_str = """SELECT sum(t.duration), wc.costs_hour
                                FROM mrp_workcenter_productivity t
                                LEFT JOIN mrp_workorder w ON (w.id = t.workorder_id)
                                LEFT JOIN mrp_workcenter wc ON (wc.id = t.workcenter_id )
                                LEFT JOIN res_users u ON (t.user_id = u.id)
                                LEFT JOIN res_partner partner ON (u.partner_id = partner.id)
                                LEFT JOIN mrp_routing_workcenter op ON (w.operation_id = op.id)
                                WHERE t.workorder_id IS NOT NULL AND t.workorder_id IN %s
                                GROUP BY w.operation_id, op.name, partner.name, t.user_id, wc.costs_hour
                                ORDER BY op.name, partner.name
                            """
                self.env.cr.execute(query_str, (tuple(Workorders.ids), ))
                for duration, cost_hour in self.env.cr.fetchall():
                    total_cost += duration / 60.0 * cost_hour
        return total_cost


    @api.model
    def _get_allocation_value(self, allocation, product_id, mo_id, quantity_sum, quantity, wip):
        ''' Computes allocation value for provided allocation 
        (one of the 4 cost recalculation models), product, mo, quantity sum and quantity, 
        for either Pack or WIP Pack. '''
        allocation_value = 0.0
        if allocation and quantity_sum:
            if not wip:
                loss_lines = allocation.allocation_line_ids.filtered(lambda l:
                    l.lp_product_id.id == product_id
                    and not l.parent_mo_id and not l.wip_pack)
            else:
                loss_lines = allocation.allocation_line_ids.filtered(lambda l:
                    l.parent_mo_id.id == line_mo_id and l.wip_pack)
            if loss_lines:
                rounding_difference = loss_lines[0].rounding_difference
                allocation_value = rounding_difference * quantity / quantity_sum
        return allocation_value


    @api.model
    def _get_allocation_rounding(self, allocation, product):
        ''' Finds rounding difference value for specified product in specified allocation. '''
        rounding_difference = 0.0
        if allocation:
            loss_lines = allocation.allocation_line_ids.filtered(lambda l:
                l.lp_product_id.id == product.id)
            if loss_lines:
                rounding_difference = loss_lines[0].rounding_difference
        return rounding_difference



class SummaryLine(models.Model):
    _name = 'cogs.report.summary.line'
    _description = 'COGS Report Summary Line'

    cogs_report_id = fields.Many2one('cogs.report', 'Parent COGS Report')
    currency_id = fields.Many2one('res.currency', 'Currency',
        related='cogs_report_id.currency_id')
    product_id = fields.Many2one('product.product', 'Product')
    product_code = fields.Char(related='product_id.default_code')
    product_name = fields.Char(related='product_id.name')
    lpus_category_id = fields.Many2one('factory.constants.lpus.category', 'LPUS Category', related='product_id.lpus_category_id')
    uom_id = fields.Many2one('uom.uom', 'Unit', related='product_id.uom_id')
    initial_quantity = fields.Integer('Quantity (Initial)', related='cogs_report_id.previous_report_id.summary_line_ids.ending_quantity')
    initial_bom_raw_material = fields.Monetary('1541C – BOM Raw Material (Initial)', related='cogs_report_id.previous_report_id.summary_line_ids.ending_raw_material')
    initial_bom_sub_material = fields.Monetary('1541P – BOM Sub Material (Initial)', related='cogs_report_id.previous_report_id.summary_line_ids.ending_sub_material')
    initial_direct_labor = fields.Monetary('622 – Direct Labor (Initial)', related='cogs_report_id.previous_report_id.summary_line_ids.ending_direct_labor')
    initial_printing_cost = fields.Monetary('1543P – Printing Cost (Initial)', related='cogs_report_id.previous_report_id.summary_line_ids.ending_printing_cost')
    initial_general_production_cost = fields.Monetary('627 – General Production Cost (Initial)', related='cogs_report_id.previous_report_id.summary_line_ids.ending_general_production_cost')
    initial_finished_goods = fields.Monetary('Finished Goods (Initial)', related='cogs_report_id.previous_report_id.summary_line_ids.ending_finished_goods')
    quantity = fields.Integer()
    ceq_quantity = fields.Float('CEQ Quantity')
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
    ending_quantity = fields.Integer('Quantity (Ending)')
    ending_raw_material = fields.Monetary('1541C – Raw Material (Ending)')
    ending_sub_material = fields.Monetary('1541P – Sub Material (Ending)')
    ending_direct_labor = fields.Monetary('622 – Direct Labor (Ending)')
    ending_printing_cost = fields.Monetary('1543P – Printing Cost (Ending)')
    ending_general_production_cost = fields.Monetary('627 – General Production Cost (Ending)')
    ending_finished_goods = fields.Monetary('Finished Goods (Ending)')


    def _compute_values(self):
        ''' Computes values of fields that are just arithmetics of previously computed fields. '''
        for line in self:
            ceq_quantity = ceq_sold_quantity = unit_cost = cogs = detail_raw_material = \
                detail_sub_material = detail_direct_labor = detail_printing_cost = \
                detail_general_production_cost = ending_raw_material = ending_sub_material = \
                ending_direct_labor = ending_printing_cost = ending_general_production_cost = \
                ending_finished_goods \
                    = 0.0
            ending_quantity = 0
            sold_quantity = line.sold_quantity # 22
            if line.product_id:
                product_ceq_factor = line.product_id.ceq_factor
                ceq_quantity = product_ceq_factor * line.quantity
                ceq_sold_quantity = product_ceq_factor * sold_quantity
            production_in_month = line.quantity + ceq_quantity + line.bom_raw_material \
                + line.bom_sub_material + line.material_loss_allocation + line.direct_labor \
                + line.labor_cost_allocation + line.printing_cost + line.printing_cost_allocation \
                + line.general_production_cost # 11 + 12 + 13 + 14 + 15 + 16 + 17 + 18 + 19 + 20
            raw_material = line.initial_bom_raw_material + line.bom_raw_material \
                + line.material_loss_allocation # 5 + 13 + 15
            sub_material = line.initial_bom_sub_material + line.bom_sub_material # 6 + 14
            direct_labor = line.initial_direct_labor + line.direct_labor \
                + line.labor_cost_allocation # 7 + 16 + 17
            print_cost = line.initial_printing_cost + line.printing_cost \
                + line.printing_cost_allocation # 8 + 18 + 19
            production_cost = line.initial_general_production_cost \
                + line.general_production_cost # 9 + 20
            quantity_sum = line.initial_quantity + line.quantity # 4 + 11

            if quantity_sum: # if 4 + 11:
                # 22 * (5 + 13 + 15) / (4 + 11)
                detail_raw_material = sold_quantity * raw_material / quantity_sum
                # 22 * (6 + 14) / (4 + 11)
                detail_sub_material = sold_quantity * sub_material / quantity_sum
                # 22 * (7 + 16 + 17) / (4 + 11)
                detail_direct_labor = sold_quantity * direct_labor / quantity_sum
                # 22 * (8 + 18 + 19) / (4 + 11)
                detail_printing_cost = sold_quantity * print_cost / quantity_sum
                # 22 * (9 + 20) / (4 + 11)
                detail_general_production_cost = sold_quantity * production_cost / quantity_sum

                cogs = detail_raw_material + detail_sub_material + detail_direct_labor \
                    + detail_printing_cost + detail_general_production_cost # 26 + 27 + 28 + 29 + 30
                if ceq_sold_quantity:
                    unit_cost = cogs / ceq_sold_quantity # 25 / 23

            ending_quantity = quantity_sum - sold_quantity # 4 + 11 - 22
            ending_raw_material = raw_material - detail_raw_material # 5 + 13 + 15 - 26
            ending_sub_material = sub_material - detail_sub_material # 6 + 14 - 27
            ending_direct_labor = direct_labor - detail_direct_labor # 7 + 16 + 17 - 28
            ending_printing_cost = print_cost - detail_printing_cost # 8 + 18 + 19 - 29
            ending_general_production_cost = production_cost - detail_general_production_cost # 9 + 20 - 30
            ending_finished_goods = line.initial_finished_goods + production_in_month - cogs # 10 + 21 - 25

            # Set values
            line.write({
                'ceq_quantity': ceq_quantity, #12
                'production_in_month': production_in_month, #21
                'ceq_sold_quantity': ceq_sold_quantity, #23
                'detail_raw_material': detail_raw_material, #26
                'detail_sub_material': detail_sub_material, #27
                'detail_direct_labor': detail_direct_labor, #28
                'detail_printing_cost': detail_printing_cost, #29
                'detail_general_production_cost': detail_general_production_cost, #30
                'cogs': cogs, #25
                'unit_cost': unit_cost, #24
                'ending_quantity': ending_quantity, #31
                'ending_raw_material': ending_raw_material, #31
                'ending_sub_material': ending_sub_material, #32
                'ending_direct_labor': ending_direct_labor, #33
                'ending_printing_cost': ending_printing_cost, #34
                'ending_general_production_cost': ending_general_production_cost, #35
                'ending_finished_goods': ending_finished_goods, #36
            })
