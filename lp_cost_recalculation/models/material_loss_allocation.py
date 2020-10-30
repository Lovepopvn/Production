# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class MaterialLossAllocation(models.Model):
    _name = 'lp_cost_recalculation.material.loss.allocation'
    _description = 'Material Loss Allocation'
    _inherit = 'lp_cost_recalculation.cost.recalculation.abstract'


    account_move_ids = fields.One2many(inverse_name='material_loss_allocation_id')
    delta_line_ids = fields.One2many('lp_cost_recalculation.material.loss.line', 'material_loss_allocation_id', 'Material Loss Lines', copy=False)
    allocation_line_ids = fields.One2many('lp_cost_recalculation.material.loss.consumed.line', 'material_loss_allocation_id', 'Material Loss Consumed Lines', copy=False)


    @api.model
    def get_calculation_type(self):
        return 'material_loss'


    inventory_adjustment_id = fields.Many2one('stock.inventory', 'Inventory Adjustment', domain=[('state', '=', 'done')], copy=False)


    def calculate_total_delta_cost(self):
        self.ensure_one_names()
        self._validate_dates()
        self._validate_state()
        if not self.inventory_adjustment_id:
            raise ValidationError(_('You must select the Inventory Adjustment first.'))
        if self.inventory_adjustment_id.state != 'done':
            raise ValidationError(_('The Inventory Adjustment selected must be Validated.'))

        inventory_adjustment_location = self._get_inventory_adjustment_location()

        # Save Inventory Adjustment's stock move lines to delta_line_ids
        stock_move_lines = self.inventory_adjustment_id.move_ids.move_line_ids
        lines = []
        for product in stock_move_lines.mapped('product_id'):
            smls_product = stock_move_lines.filtered(lambda l: l.product_id.id == product.id)
            delta_quantity = 0
            for sml in smls_product:
                if sml.location_dest_id.id == inventory_adjustment_location.id:
                    delta_quantity += sml.qty_done
                else:
                    delta_quantity -= sml.qty_done
            lines.append((0, 0, {'material_id': product.id, 'delta_quantity': delta_quantity}))
        self.write({'delta_line_ids': lines})

        AccountMoveLine = self.env['account.move.line'] # Journal Item
        account_move_lines_in_moves = AccountMoveLine.search([('move_id.stock_move_id.id', 'in', self.inventory_adjustment_id.move_ids.ids)])
        account_move_lines = account_move_lines_in_moves.filtered(lambda r: r.account_id.id == r.move_id.stock_move_id.product_id.categ_id.property_stock_valuation_account_id.id)

        for loss_line in self.delta_line_ids:
            amls_product = account_move_lines.filtered(lambda l: l.product_id.id == loss_line.material_id.id)
            # Commented out - new logic is to allow materials without JIs
            # if not amls_product:
            #     raise UserError(_("Couldn't find Journal Item(s) for the loss line of material %s.") % loss_line.material_id.name_get()[0][1])
            delta_cost = 0.0
            for aml in amls_product:
                if aml.debit:
                    delta_cost -= aml.debit
                else:
                    delta_cost += aml.credit
            loss_line.write({'delta_cost': delta_cost})


    def compute_allocation(self):
        self.ensure_one_names()

        self.calculate_total_delta_cost()

        self._validate_journal_company()

        StockMove = self.env['stock.move']
        material_ids = self.delta_line_ids.mapped('material_id.id')
        stock_moves_all_components = StockMove.search([('raw_material_production_id.state', '=', 'done'), ('raw_material_production_id.date_finished', '>=', self.date_from), ('raw_material_production_id.date_finished', '<=', self.date_to), ('product_id.id', 'in', material_ids)])
        manufacturing_orders_all = stock_moves_all_components.raw_material_production_id
        self._validate_product_ceq_factor(manufacturing_orders_all)

        for loss_line in self.delta_line_ids:
            material_id = loss_line.material_id.id
            stock_moves_components = StockMove.search([('raw_material_production_id.state', '=', 'done'), ('raw_material_production_id.date_finished', '>=', self.date_from), ('raw_material_production_id.date_finished', '<=', self.date_to), ('product_id.id', '=', material_id)])
            manufacturing_orders = stock_moves_components.raw_material_production_id
            lines = []
            for manufacturing_order in manufacturing_orders:
                line_vals = self._get_allocation_line_vals(manufacturing_order, process_ceq=True)
                line_vals.update({
                    'material_id': material_id,
                    'delta_line_id': loss_line.id
                })
                lines.append((0, 0, line_vals))
            self.write({'allocation_line_ids': lines})
        self._process_allocation_lines()
        self.write({'state': 'allocation_derived'})


    def validate(self):
        self.ensure_one_names()
        self._create_journal_entries()
        self._update_costs()
        self.write({'state': 'posted'})


    def export_allocation_lines(self):
        return self._export_allocation_lines()

class MaterialLossLine(models.Model):
    _name = 'lp_cost_recalculation.material.loss.line'
    _description = 'Material Loss Line'

    material_id = fields.Many2one('product.product', 'Material')
    delta_quantity = fields.Integer()
    delta_cost = fields.Monetary()
    material_loss_allocation_id = fields.Many2one('lp_cost_recalculation.material.loss.allocation', 'Parent Material Loss Allocation')
    currency_id = fields.Many2one(related='material_loss_allocation_id.currency_id')

class MaterialLossConsumedLine(models.Model):
    _name = 'lp_cost_recalculation.material.loss.consumed.line'
    _description = 'Material Loss Consumed Line'
    _inherit = 'lp_cost_recalculation.abstract.allocation.line'

    material_id = fields.Many2one('product.product', 'Material')
    ceq_factor = fields.Float('CEQ Factor')
    ceq_converted_qty = fields.Float('CEQ Converted Quantity')
    material_loss_allocation = fields.Float(digits=(32,4))
    material_loss_allocation_id = fields.Many2one('lp_cost_recalculation.material.loss.allocation', 'Parent Material Loss Allocation')
    delta_line_id = fields.Many2one('lp_cost_recalculation.material.loss.line', 'Origin Material Loss Line')
    currency_id = fields.Many2one('res.currency', string='Currency', related='material_loss_allocation_id.currency_id')
