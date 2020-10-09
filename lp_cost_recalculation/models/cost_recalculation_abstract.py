# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.http_routing.models.ir_http import slugify
from odoo.tools.misc import xlsxwriter

from datetime import datetime
from dateutil.relativedelta import relativedelta
import io, base64


# months in int - str tuples
MONTHS = [(str(month), '%02d' % month) for month in list(range(1, 13))]

TIMEZONE_RELATIVEDELTA = relativedelta(hours=7)

STATES = [('draft', 'Draft'), ('allocation_derived', 'Allocation Derived'), ('posted', 'Posted')]
DEFAULT_STATE = STATES[0][0]

MODEL_NAMES = {
    'material_loss': _('Material Loss Allocation'),
    'labor_cost': _('Labor Cost Allocation'),
    'click_charge': _('Click Charge Allocation'),
    'overhead_cost': _('Overhead Cost Allocation'),
}

SPECIFIC_FIELDS = {
    'material_loss': {'je_inverse_field': 'material_loss_allocation_id'},
    'labor_cost': {'je_inverse_field': 'labor_cost_allocation_id'},
    'click_charge': {'je_inverse_field': 'click_charge_allocation_id'},
    'overhead_cost': {'je_inverse_field': 'overhead_cost_allocation_id'},
}

class AbstractCostRecalculation(models.AbstractModel):
    _name = 'lp_cost_recalculation.cost.recalculation.abstract'
    _description = 'Abstract Cost Recalculation - common fields and functions'
    _order = 'date_to desc, id desc'

    @api.model
    def _get_available_years(initial_year=2020):
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

    def _validate_journal_company(self):
        for record in self:
            if not record.journal_id:
                raise ValidationError(_('You must select the Journal first.'))
            if not record.company_id:
                raise ValidationError(_('The Company is not selected. Please check the selected Journal has a Company assigned.'))

    def ensure_one_names(self):
        try:
            self.ensure_one()
        except:
            record_names = [r.name_get()[0][1] for r in self]
            record_names_string = "\n".join(record_names)
            raise ValidationError(_("Only one record can be processed at a time. Records you tried to process:\n\n%s") % record_names_string)

    _default_year = lambda l: str((datetime.now()+TIMEZONE_RELATIVEDELTA).year)
    _default_month = lambda l: str((datetime.now()+TIMEZONE_RELATIVEDELTA).month)

    name = fields.Char(required=True)
    state = fields.Selection(STATES, default=DEFAULT_STATE, copy=False)
    account_move_ids = fields.One2many('account.move', 'material_loss_allocation_id', 'Journal Entries', copy=False)
    account_move_count = fields.Integer('JE Count', compute='_compute_move_count', store=False)
    year = fields.Selection(_get_available_years(), default=_default_year)
    month = fields.Selection(MONTHS, default=_default_month)
    date_from = fields.Datetime(compute='_compute_date_range', store=True)
    date_to = fields.Datetime(compute='_compute_date_range', store=True)
    journal_id = fields.Many2one('account.journal', 'Journal')
    company_id = fields.Many2one('res.company', 'Company', related='journal_id.company_id')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.company.currency_id.id)
    allocation_lines_xlsx = fields.Binary('Allocation Lines XLSX', readonly=True, copy=False)
    allocation_lines_xlsx_filename = fields.Char(compute='_compute_xls_name')
    allocation_rounding_difference = fields.Float()


    @api.model
    def get_model_name(self):
        calculation_type = self.get_calculation_type()
        return MODEL_NAMES[calculation_type]


    @api.model
    def get_specific_field_names(self):
        calculation_type = self.get_calculation_type()
        return SPECIFIC_FIELDS[calculation_type]


    @api.depends('account_move_ids')
    def _compute_move_count(self):
        for record in self:
            record.account_move_count = len(record.account_move_ids)


    @api.depends('year', 'month')
    def _compute_date_range(self):
        for record in self:
            if record.year and record.month:
                date_from = datetime(int(record.year), int(record.month), 1)
                date_to = date_from + relativedelta(months=1) - relativedelta(seconds=1)
                if date_from > datetime.now():
                    raise ValidationError(_("You can't select a month that hasn't started yet."))
                record.date_from = date_from - TIMEZONE_RELATIVEDELTA
                record.date_to = date_to - TIMEZONE_RELATIVEDELTA
            else:
                record.date_from = record.date_to = False


    @api.depends('year', 'month', 'name')
    def _compute_xls_name(self):
        for record in self:
            if record.year and record.month:
                filename = '%s/%02d %s' % (record.year, int(record.month), record.name)
                filename = slugify(filename) + '.xlsx'
            else:
                filename = 'allocation.xlsx'
            record.allocation_lines_xlsx_filename = filename


    def button_draft(self):
        self._validate_state(1)
        self.write({
            'delta_line_ids': (5, 0, 0),
            'allocation_line_ids': (5, 0, 0),
            'state': 'draft',
            'allocation_lines_xlsx': False,
        })


    def unlink(self):
        for record in self:
            if record.state == 'posted':
                raise ValidationError(_('Record "%s" cannot be deleted because it has already been posted.') % record.name_get()[0][1])
        return super(AbstractCostRecalculation, self).unlink()


    def action_view_related_move_lines(self):
        self.ensure_one_names()
        je_inverse_field = self.get_specific_field_names()['je_inverse_field']
        domain = [(je_inverse_field, '=', self.id)]
        template_list = self.env.ref('account.view_move_tree')
        template_form = self.env.ref('account.view_move_form')
        action = {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_type': 'list',
            'view_mode': 'list,form',
            'view_id': template_list.id,
            'views': [(template_list.id, 'list'), (template_form.id, 'form')],
            'domain': domain,
        }
        return action


    @api.model
    def _get_inventory_adjustment_location(self):
        # Get default location for inventory adjustments
        Models = self.env['ir.model']
        product_template_model_id = Models.search([('model', '=', 'product.template')])[0].id
        Fields = self.env['ir.model.fields']
        property_field_id = Fields.search([('name', '=', 'property_stock_inventory'), ('model_id', '=', product_template_model_id)])[0].id
        CompanyProperties = self.env['ir.property']
        property_stock_inventory = CompanyProperties.search([('fields_id.id', '=', property_field_id), ('res_id', '=', False)])
        if not property_stock_inventory:
            raise UserError(_("Company property storing default Inventory Adjustment Location couldn't be found."))
        if len(property_stock_inventory) > 1:
            raise UserError(_("There are more than one company properties storing default Inventory Adjustment Location. Please make sure your master data are set correctly."))
        value_reference_list = property_stock_inventory[0].value_reference.split(',')
        if len(value_reference_list) != 2:
            raise UserError(_("Something went wrong when loading default Inventory Adjustment Location. Please make sure your master data are set correctly."))
        if value_reference_list[0] != 'stock.location':
            raise UserError(_("When loading default Inventory Adjustment Location, the record referenced was not a location. Please make sure your master data are set correctly."))
        StockLocation = self.env[value_reference_list[0]]
        inventory_adjustment_locations = StockLocation.browse([int(value_reference_list[1])])
        if len(inventory_adjustment_locations) != 1:
            raise UserError(_("When loading default Inventory Adjustment Location, the record wasn't found. Please make sure your master data are set correctly."))
        inventory_adjustment_location = inventory_adjustment_locations[0]
        return inventory_adjustment_location


    def _get_manufacturing_orders(self):
        self.ensure_one_names()
        ManufacturingOrder = self.env['mrp.production']
        search_domain = [('state', '=', 'done'), ('date_finished', '>=', self.date_from), ('date_finished', '<=', self.date_to)]
        manufacturing_orders = ManufacturingOrder.search(search_domain)
        return manufacturing_orders


    @api.model
    def _validate_mo_finished_product(self, manufacturing_order):
        if not manufacturing_order.finished_move_line_ids:
            raise UserError(_("Couldn't find a Finished Product for Manufacturing Order %s.") % manufacturing_order.name)
        if len(manufacturing_order.finished_move_line_ids) > 1:
            raise UserError(_("Found more than one Finished Product for Manufacturing Order %s.") % manufacturing_order.name)


    @api.model
    def _get_finished_product_line(self, manufacturing_order):
        self._validate_mo_finished_product(manufacturing_order)
        finished_product_line = manufacturing_order.finished_move_line_ids[0]
        return finished_product_line


    def _validate_product_ceq_factor(self, manufacturing_orders):
        names = []
        for manufacturing_order in manufacturing_orders:
            finished_product_line = self._get_finished_product_line(manufacturing_order)
            if not finished_product_line.product_id.ceq_factor:
                name = finished_product_line.product_id.name_get()[0][1]
                if name not in names:
                    names.append(name)
        if names:
            message_start = _('CEQ Factor is not set for following product(s):')
            message_products = '\n'.join(names)
            message = message_start + '\n\n' + message_products
            raise ValidationError(message)


    @api.model
    def _get_allocation_line_vals(self, manufacturing_order, process_ceq=False):
        ''' Prepares lines for common allocation lines model from provided Manufacturing Order '''
        lp_product = manufacturing_order.product_id
        mo_id = manufacturing_order.id
        parent_mo = manufacturing_order.parent_mo_id
        finished_product_line = self._get_finished_product_line(manufacturing_order)
        lp_qty = finished_product_line.qty_done
        shipped_qty_lp = 0
        for product_lot in manufacturing_order.product_lot_ids:
            picking_wave = product_lot.picking_wave_id
            if picking_wave and picking_wave.shipping_status == 'shipped':
                shipped_qty_lp += product_lot.number_of_items
        pa_product_id = False
        pa_qty = 0
        shipped_qty_pa = 0
        wip_pack = False
        if parent_mo:
            pa_product_id = parent_mo.product_id.id
            if parent_mo.state != 'done':
                wip_pack = True
            else:
                finished_product_line_pa = self._get_finished_product_line(parent_mo)
                pa_qty = finished_product_line_pa.qty_done
                for product_lot in parent_mo.product_lot_ids:
                    picking_wave = product_lot.picking_wave_id
                    if picking_wave and picking_wave.shipping_status == 'shipped':
                        shipped_qty_pa += product_lot.number_of_items
        line_vals = {
            'lp_product_id': lp_product.id,
            'wip_pack': wip_pack,
            'mo_id': mo_id,
            'parent_mo_id': parent_mo.id,
            'pa_product_id': pa_product_id,
            'lp_qty': lp_qty,
            'pa_qty': pa_qty,
            'shipped_qty_lp': shipped_qty_lp,
            'shipped_qty_pa': shipped_qty_pa,
        }
        if process_ceq:
            ceq_factor = finished_product_line.product_id.ceq_factor
            if not ceq_factor:
                raise ValidationError(_('CEQ Factor for product "%s" is not set.') % \
                    finished_product_line.product_id.name_get()[0][1])
            ceq_converted_qty = lp_qty * ceq_factor
            line_vals.update({
                'ceq_factor': ceq_factor,
                'ceq_converted_qty': ceq_converted_qty,
            })
        return line_vals


    def _process_allocation_lines(self):
        self.ensure_one_names()
        calculation_type = self.get_calculation_type()
        manufacturing_orders = self.allocation_line_ids.mapped('mo_id')

        if calculation_type == 'material_loss':
            allocated_value_field = 'material_loss_allocation'
            ceq_converted_qty_material = {}
            for line in self.allocation_line_ids:
                if line.material_id.id in ceq_converted_qty_material:
                    ceq_converted_qty_material[line.material_id.id] += line.ceq_converted_qty
                else:
                    ceq_converted_qty_material[line.material_id.id] = line.ceq_converted_qty
        elif calculation_type == 'labor_cost':
            allocated_value_field = 'gap_allocated_value'
            total_workcenter_cost = {}
            workcenters = self.allocation_line_ids.mapped('workcenter_id')
            for workcenter in workcenters:
                workcenter_delta_lines = self.delta_line_ids.filtered(lambda r: r.workcenter_id.id == workcenter.id)
                total_cost = sum(workcenter_delta_lines.mapped('calculated_labor_cost'))
                total_workcenter_cost[workcenter.id] = total_cost
        elif calculation_type == 'click_charge':
            allocated_value_field = 'allocated_value'
            total_calculated_cost = sum(self.delta_line_ids.mapped('calculated_cost'))
        elif calculation_type == 'overhead_cost':
            allocated_value_field = 'overhead_cost_allocation'
            total_overhead_cost = sum(self.delta_line_ids.mapped('actual_cost'))
            total_ceq_converted_qty = sum(self.allocation_line_ids.mapped('ceq_converted_qty'))

        for manufacturing_order in manufacturing_orders:
            mo_consumed_lines = self.allocation_line_ids.filtered(lambda r: r.mo_id.id == manufacturing_order.id)

            lines = []
            for line in mo_consumed_lines:

                if calculation_type == 'material_loss':
                    allocation_ratio = ceq_converted_qty_material[line.material_id.id] / line.ceq_converted_qty
                elif calculation_type == 'labor_cost':
                    allocation_ratio = total_workcenter_cost[line.workcenter_id.id] / line.calculated_cost
                elif calculation_type == 'click_charge':
                    allocation_ratio = total_calculated_cost / line.calculated_cost
                if calculation_type == 'overhead_cost':
                    allocation_ratio = total_ceq_converted_qty / line.ceq_converted_qty

                if calculation_type == 'overhead_cost':
                    allocated_value = total_overhead_cost / allocation_ratio
                else:
                    allocated_value = line.delta_line_id.delta_cost / allocation_ratio

                if calculation_type == 'click_charge':
                    cogs_allocated_lp = (allocated_value + line.calculated_cost) * line.shipped_qty_lp / line.lp_qty
                else:
                    cogs_allocated_lp = allocated_value * line.shipped_qty_lp / line.lp_qty

                line_vals = {
                    'allocation_ratio': allocation_ratio,
                    allocated_value_field: allocated_value,
                    'cogs_allocated_lp': cogs_allocated_lp,
                }

                if line.pa_product_id:
                    cogs_allocated_pa = allocated_value * line.shipped_qty_pa / line.pa_qty
                    line_vals.update({
                        'cogs_allocated_pa': cogs_allocated_pa,
                    })
                lines.append((1, line.id, line_vals))
            self.write({'allocation_line_ids': lines})
            # If too memory-heavy in production, line write (Postgre RAM / disk cache) 
            # could be moved inside the line for loop and not kept in list (Python RAM)

        parent_mo_ids = self.allocation_line_ids.parent_mo_id.ids
        rounding_difference_sum = 0.0
        for lp_product in self.allocation_line_ids.mapped('lp_product_id'):
            lines_product = self.allocation_line_ids.filtered(lambda l: 
                l.lp_product_id.id == lp_product.id and not l.parent_mo_id)

            lines_lp = lines_product.filtered(lambda l: 
                not l.parent_mo_id and l.mo_id.id not in parent_mo_ids)
            lines_pa = lines_product.filtered(lambda l: 
                not l.parent_mo_id and l.mo_id.id in parent_mo_ids)
            lines_lp_wip = lines_product.filtered(lambda l: 
                l.parent_mo_id and l.wip_pack)
            rounding_difference_sum += self._calculate_unit_cost_to_adjust(
                allocated_value_field, lines_lp, lp_product)
            rounding_difference_sum += self._calculate_unit_cost_to_adjust(
                allocated_value_field, lines_pa, lp_product, 'pa')
            rounding_difference_sum += self._calculate_unit_cost_to_adjust(
                allocated_value_field, lines_lp_wip, lp_product, wip_pack=True)

        cost_type = 'delta_cost'
        if calculation_type == 'overhead_cost':
            cost_type = 'actual_cost'
        if calculation_type == 'material_loss':
            allocated_material_ids = self.allocation_line_ids.material_id.ids
            delta_lines = self.delta_line_ids.filtered(
                lambda l: l.material_id.id in allocated_material_ids)
            total_delta_cost = sum(delta_lines.mapped(cost_type))
        else:
            total_delta_cost = sum(self.mapped('delta_line_ids.' + cost_type))
        allocation_rounding_difference = rounding_difference_sum - total_delta_cost
        self.write({'allocation_rounding_difference': allocation_rounding_difference})


    def _calculate_unit_cost_to_adjust(self, allocated_value_field, lines, lp_product, product_type='lp', wip_pack=False):
        self.ensure_one_names()
        rounding_difference = 0.0
        if lines:
            if wip_pack:
                allocation_sum = sum(lines.mapped(allocated_value_field))
            else:
                allocation_sum = sum(lines.mapped(
                    lambda l: l[allocated_value_field] - l.cogs_allocated_lp))
            if product_type == 'pa':
                mo_ids = lines.mo_id.ids
                parent_mo_lines = self.allocation_line_ids.filtered(
                    lambda l: l.parent_mo_id.id in mo_ids)
                parent_mo_allocation_sum = sum(parent_mo_lines.mapped(allocated_value_field))
                allocation_sum += parent_mo_allocation_sum

            product_on_hand_qty, product_on_hand_value = self._get_on_hand(lp_product)
            unit_cost_to_adjust = 0
            if product_on_hand_qty:
                unit_cost_to_adjust = (allocation_sum + product_on_hand_value) / product_on_hand_qty
                allocation_qty = product_on_hand_qty
            else:
                mo_lp_qty = {l.mo_id.id: l.lp_qty for l in lines}
                lp_qty_sum = sum(mo_lp_qty.values())
                unit_cost_to_adjust = (allocation_sum + product_on_hand_value) / lp_qty_sum
                allocation_qty = lp_qty_sum
            lines.write({
                'product_on_hand_qty': product_on_hand_qty,
                'product_on_hand_value': product_on_hand_value,
                'unit_cost_to_adjust_by_' + product_type: unit_cost_to_adjust,
            })

            unit_cost_to_adjust_rounded = lines[0]['unit_cost_to_adjust_by_' + product_type]
            cogs_allocated = sum(lines.mapped('cogs_allocated_lp'))
            rounding_difference = unit_cost_to_adjust_rounded * allocation_qty \
                - product_on_hand_value + cogs_allocated
            lines.write({
                'rounding_difference': rounding_difference,
            })

        return rounding_difference


    @api.model
    def _get_on_hand(self, product):
        domain_loc = product._get_domain_locations()[0] # taken from _search_on_hand of stock.quant
        quants = self.env['stock.quant'].search([('product_id', '=', product.id)] + domain_loc)
        on_hand_qty = sum(quants.mapped('quantity'))
        on_hand_value = sum(quants.mapped('value'))
        return on_hand_qty, on_hand_value


    @api.model
    def _get_account_error(self, account_name, category=0):
        category_name = False
        if category == 0:
            category_name = 'COGS Allocation Accounts'
        elif category == 1:
            category_name = 'Make to Stock Allocation Accounts'
        elif category == 2:
            category_name = 'WIP Pack Allocation Accounts'
        return '%s%s' % (category_name and category_name + ' - ' or '', account_name)


    @api.model
    def _raise_account_error(self, account_name, category=0):
        account = self._get_account_error(account_name, category)
        error = _("You must set the %s in Accounting Settings - Product Cost Allocation Accounts.") % account
        raise ValidationError(error)


    @api.model
    def _validate_je_accounts(self):
        calculation_type = self.get_calculation_type()
        errors = []
        if not self.company_id.cogs_allocation_valuation_account_id:
            errors.append(self._get_account_error('Valuation Account'))

        if calculation_type == 'material_loss':
            error_account_name = 'Counterpart Account For Material Loss'
            if not self.company_id.cogs_allocation_counterpart_account_material_loss_id:
                errors.append(self._get_account_error(error_account_name))
            if not self.company_id.make_to_stock_allocation_counterpart_account_material_loss_id:
                errors.append(self._get_account_error(error_account_name, 1))
            if not self.company_id.wip_pack_allocation_counterpart_account_material_loss_id:
                errors.append(self._get_account_error(error_account_name, 2))
        elif calculation_type == 'labor_cost':
            error_account_name = 'Counterpart Account For Direct Labor'
            if not self.company_id.cogs_allocation_counterpart_account_direct_labor_id:
                errors.append(self._get_account_error(error_account_name))
            if not self.company_id.make_to_stock_allocation_counterpart_account_direct_labor_id:
                errors.append(self._get_account_error(error_account_name, 1))
            if not self.company_id.wip_pack_allocation_counterpart_account_direct_labor_id:
                errors.append(self._get_account_error(error_account_name, 2))
        elif calculation_type == 'click_charge':
            error_account_name = 'Counterpart Account For Click Charge'
            if not self.company_id.cogs_allocation_counterpart_account_click_charge_id:
                errors.append(self._get_account_error(error_account_name))
            if not self.company_id.make_to_stock_allocation_counterpart_account_click_charge_id:
                errors.append(self._get_account_error(error_account_name, 1))
            if not self.company_id.wip_pack_allocation_counterpart_account_click_charge_id:
                errors.append(self._get_account_error(error_account_name, 2))
        elif calculation_type == 'overhead_cost':
            error_account_name = 'Counterpart Account For Overhead Cost'
            if not self.company_id.cogs_allocation_counterpart_account_overhead_cost_id:
                errors.append(self._get_account_error(error_account_name))
            if not self.company_id.make_to_stock_allocation_counterpart_account_overhead_cost_id:
                errors.append(self._get_account_error(error_account_name, 1))
            if not self.company_id.wip_pack_allocation_counterpart_account_overhead_cost_id:
                errors.append(self._get_account_error(error_account_name, 2))

        if errors:
            missing_accounts_lines = '\n'.join(errors)
            raise ValidationError(_("This operation cannot be processed because necessary accounts are not selected in Accounting Settings - Product Cost Allocation Accounts.") + '\n\n' + _("Missing accounts:") + '\n' + missing_accounts_lines)


    def _create_journal_entries(self):
        self.ensure_one_names()
        self._validate_state(1)
        self._validate_journal_company()
        self._validate_je_accounts()

        lp_products = self.allocation_line_ids.mapped('lp_product_id')
        pa_products = self.allocation_line_ids.mapped('pa_product_id')
        products = set(lp_products + pa_products)

        accounts = self._get_accounts()

        for product in products:
            lines_lp = self.allocation_line_ids.filtered(lambda r: r.lp_product_id.id == product.id and not r.parent_mo_id)
            je_amount = sum(lines_lp.mapped('cogs_allocated_lp'))
            lines_pa = self.allocation_line_ids.filtered(lambda r: r.pa_product_id.id == product.id)
            lines = lines_lp + lines_pa
            je_amount += sum(lines.mapped('cogs_allocated_pa'))
            if je_amount != 0:
                self._create_journal_entry(je_amount, product, accounts)

        self.account_move_ids.action_post()


    def _create_journal_entry(self, je_amount, product, accounts):
        self.ensure_one_names()
        if je_amount == 0:
            return

        # Create JE
        name = product.name_get()[0][1]
        code = product.default_code
        ref = _('COGS %s – %s') % (self.get_model_name(), code)
        on_hand_qty, on_hand_value = self._get_on_hand(product)
        date = fields.Date.today()
        journal_id = self.journal_id.id
        amount_1 = je_amount > 0 and je_amount or 0.0
        amount_2 = je_amount <= 0 and - je_amount or 0.0
        lines = [
            (0, 0, {
                'account_id': accounts['cogs_valuation'],
                'debit': amount_1,
                'credit': amount_2,
                'name': name,
                'ref': ref,
            }),
            (0, 0, {
                'account_id': accounts['cogs_counterpart'],
                'debit': amount_2,
                'credit': amount_1,
                'name': name,
                'ref': ref,
            }),
        ]

        if not on_hand_qty:
            lines += [
                (0, 0, {
                    'account_id': accounts['cogs_counterpart'],
                    'debit': amount_1,
                    'credit': amount_2,
                    'name': name,
                    'ref': ref,
                }),
                (0, 0, {
                    'account_id': accounts['make_to_stock_counterpart'],
                    'debit': amount_2,
                    'credit': amount_1,
                    'name': name,
                    'ref': ref,
                }),
            ]

        je_inverse_field = self.get_specific_field_names()['je_inverse_field']
        self.write({
            'account_move_ids': [(0, 0, {
                'date': date,
                'journal_id': journal_id,
                'ref': ref,
                'line_ids': lines,
                je_inverse_field: self.id
            })]
        })


    @api.model
    def _get_accounts(self):
        calculation_type = self.get_calculation_type()
        cogs_valuation = self.company_id.cogs_allocation_valuation_account_id
        cogs_counterpart = False
        make_to_stock_counterpart = False

        if calculation_type == 'material_loss':
            cogs_counterpart = self.company_id.cogs_allocation_counterpart_account_material_loss_id
            make_to_stock_counterpart = self.company_id.make_to_stock_allocation_counterpart_account_material_loss_id
            wip_counterpart = self.company_id.wip_pack_allocation_counterpart_account_material_loss_id
        elif calculation_type == 'labor_cost':
            cogs_counterpart = self.company_id.cogs_allocation_counterpart_account_direct_labor_id
            make_to_stock_counterpart = self.company_id.make_to_stock_allocation_counterpart_account_direct_labor_id
            wip_counterpart = self.company_id.wip_pack_allocation_counterpart_account_direct_labor_id
        elif calculation_type == 'click_charge':
            cogs_counterpart = self.company_id.cogs_allocation_counterpart_account_click_charge_id
            make_to_stock_counterpart = self.company_id.make_to_stock_allocation_counterpart_account_click_charge_id
            wip_counterpart = self.company_id.wip_pack_allocation_counterpart_account_click_charge_id
        elif calculation_type == 'overhead_cost':
            cogs_counterpart = self.company_id.cogs_allocation_counterpart_account_overhead_cost_id
            make_to_stock_counterpart = self.company_id.make_to_stock_allocation_counterpart_account_overhead_cost_id
            wip_counterpart = self.company_id.wip_pack_allocation_counterpart_account_overhead_cost_id

        return {
            'cogs_valuation': cogs_valuation.id,
            'cogs_counterpart': cogs_counterpart.id,
            'make_to_stock_counterpart': make_to_stock_counterpart.id,
            'wip_counterpart': wip_counterpart.id,
        }


    def _update_costs(self): #counterpart_id, wip_counterpart_id):
        self.ensure_one_names()
        accounts = self._get_accounts()
        counterpart_id = accounts['make_to_stock_counterpart']
        wip_counterpart_id = accounts['wip_counterpart']

        # Update LP Product Cost
        self._update_costs_category(counterpart_id)
        self._update_costs_category(wip_counterpart_id, wip=True)
        # Update PA Product Cost
        self._update_costs_category(counterpart_id, 'pa')


    def _update_costs_category(self, counterpart_id, category='lp', wip=False):
        self.ensure_one_names()
        if wip:
            lines = self.allocation_line_ids.filtered(
                lambda l: l['unit_cost_to_adjust_by_' + category] and l.wip_pack)
        else:
            lines = self.allocation_line_ids.filtered(
                lambda l: l['unit_cost_to_adjust_by_' + category] and not l.wip_pack)
        products = lines.mapped('lp_product_id')
        for product in products:
            lines_product = lines.filtered(lambda r: r.lp_product_id.id == product.id)
            if lines_product:
                ref = _('%s – %s') % (self.get_model_name(), product.default_code)
                new_cost = lines_product[0]['unit_cost_to_adjust_by_' + category]
                product._change_standard_price(new_cost, 
                    counterpart_account_id=counterpart_id, ref=ref)


    def _export_allocation_lines(self):
        calculation_type = self.get_calculation_type()
        headers, lines_values = self._get_allocation_lines_data()

        report_name = '%s-%02d %s' % (self.year, int(self.month), self.name)
        report_name = slugify(report_name)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(calculation_type)

        style_header = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bg_color': '#eeeeee'})
        style_data = workbook.add_format({'font_name': 'Arial'})

        offset_x = 0
        offset_y = 0
        for header in headers:
            sheet.write(offset_y, offset_x, header, style_header)
            offset_x += 1

        for row in lines_values:
            offset_y += 1
            offset_x = 0
            for value in row:
                sheet.write(offset_y, offset_x, value, style_data)
                offset_x += 1

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        self.write({'allocation_lines_xlsx': base64.encodebytes(generated_file)})


    def _get_allocation_lines_data(self):
        calculation_type = self.get_calculation_type()
        self.ensure_one_names()

        columns_start = {
            'material_loss': ['material_id'],
            'labor_cost': ['workcenter_id'],
            'click_charge': [],
            'overhead_cost': [],
        }
        columns_start_common = [
            'lp_product_id',
            'wip_pack',
            'mo_id',
            'parent_mo_id',
            'pa_product_id',
            'lp_qty',
            'pa_qty',
            'product_on_hand_qty',
            'product_on_hand_value',
        ]
        columns_calculated = {
            'material_loss': [
                'ceq_factor',
                'ceq_converted_qty',
            ],
            'labor_cost': ['calculated_cost'],
            'click_charge': ['calculated_cost'],
            'overhead_cost': [
                'ceq_factor',
                'ceq_converted_qty',
            ],
        }
        columns_mid_common = [
            'allocation_ratio',
        ]
        columns_mid = {
            'material_loss': ['material_loss_allocation'],
            'labor_cost': ['gap_allocated_value'],
            'click_charge': ['allocated_value'],
            'overhead_cost': ['overhead_cost_allocation'],
        }
        columns_end_common = [
            'shipped_qty_lp',
            'shipped_qty_pa',
            'cogs_allocated_lp',
            'cogs_allocated_pa',
            'unit_cost_to_adjust_by_lp',
            'unit_cost_to_adjust_by_pa',
            'rounding_difference',
        ]

        columns = columns_start[calculation_type] + columns_start_common + columns_calculated[calculation_type] + columns_mid_common + columns_mid[calculation_type] + columns_end_common

        fields = self.allocation_line_ids.fields_get()
        headers = [fields[field]['string'] for field in columns]

        lines_values = []
        for line in self.allocation_line_ids:
            line_values = []
            for field in columns:
                field_content = line[field]
                if field[-3:] == '_id':
                    if len(field_content) > 0:
                        line_values.append(field_content.name_get()[0][1])
                    else:
                        line_values.append('')
                elif isinstance(field_content, (int, float)):
                    line_values.append(field_content)
                else:
                    line_values.append(str(field_content))
            lines_values.append(line_values)

        return headers, lines_values


class AbstractAllocationLine(models.AbstractModel):
    _name = 'lp_cost_recalculation.abstract.allocation.line'
    _description = 'Abstract Allocation Line - common fields'

    lp_product_id = fields.Many2one('product.product','LP Product')
    wip_pack = fields.Boolean('In a WIP Pack')
    mo_id = fields.Many2one('mrp.production','MO')
    parent_mo_id = fields.Many2one('mrp.production','Parent MO')
    pa_product_id = fields.Many2one('product.product','PA Product')
    lp_qty = fields.Integer('LP Quantity')
    pa_qty = fields.Integer('PA Quantity')
    product_on_hand_qty = fields.Integer('Product On Hand Quantity')
    product_on_hand_value = fields.Float('Product On Hand Value')
    allocation_ratio = fields.Float()
    shipped_qty_lp = fields.Integer('Shipped Quantity LP')
    shipped_qty_pa = fields.Integer('Shipped Quantity PA')
    cogs_allocated_lp = fields.Monetary('COGS Allocated LP')
    cogs_allocated_pa = fields.Monetary('COGS Allocated PA')
    unit_cost_to_adjust_by_lp = fields.Monetary('Unit Cost To Adjust By LP')
    unit_cost_to_adjust_by_pa = fields.Monetary('Unit Cost To Adjust By PA')
    rounding_difference = fields.Float()
    currency_id = fields.Many2one('res.currency', string='Currency')
