# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _account_entry_move(self, qty, description, svl_id, cost):
        ''' Overridden base stock_account/models/stock_move.py:455 to add logic for splitting JE's cost into two accounts (Operations, Components) when marking Manufacturing Order done - this function checks whether this is MO's final product or a regular stock move, and if it is the final product, forwards selected Operations cost account ID via context '''
        self.ensure_one()
        if self.product_id.type != 'product':
            # no stock valuation for consumable products
            return False
        if self.restrict_partner_id:
            # if the move isn't owned by the company, we don't make any valuation
            return False

        location_from = self.location_id

        if not (self._is_in() and location_from and location_from.usage == 'production' and self.production_id):
            # Not a finished product - proceed with base Odoo logic
            res = super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)
            return res

        # Port Cities
        location_from.validate_valuation_accounts()
        acc_src_operation_id = location_from.operation_valuation_out_account_id.id
        acc_src_printing_id = location_from.printing_valuation_out_account_id.id

        click_rate = 0
        factory_constants = self.env.company.factory_constants_id
        if factory_constants:
            click_rate = factory_constants.average_printing_cost
        total_printed_sides = sum(self.production_id.follower_sheets_ids.mapped('total_printed_side'))
        printing_cost = round(total_printed_sides * click_rate)

        company_to = self._is_in() and self.mapped('move_line_ids.location_dest_id.company_id') or False
        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
        self.with_context(force_company=company_to.id, acc_src_operation_id=acc_src_operation_id, acc_src_printing_id=acc_src_printing_id, printing_cost=printing_cost)._create_account_move_line(acc_src, acc_valuation, journal_id, qty, description, svl_id, cost)

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description):
        ''' Overridden base stock_account/models/stock_move.py:378 to add logic for splitting JE's cost into two accounts (Operations, Components) when marking Manufacturing Order done - this function prepares JE lines '''

        res = super(StockMove, self)._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description)
        acc_src_operation_id = self._context.get('acc_src_operation_id')
        acc_src_printing_id = self._context.get('acc_src_printing_id')

        if not (acc_src_operation_id and acc_src_printing_id):
            # This is not a JE for a finished product of an MO - process as usual
            return res

        # Preparing data of JE for a finished product of an MO
        debit_line_vals = res['debit_line_vals']

        # Based on the logic of mrp_account_enterprise/reports/mrp_cost_structure.py:23 for getting operations costs of an MO (SQL simplified and summed)
        query_str = """
            SELECT SUM(total_cost) FROM 
            (SELECT sum(t.duration) / 60 * wc.costs_hour "total_cost"
            FROM mrp_workcenter_productivity t
            LEFT JOIN mrp_workorder w ON (w.id = t.workorder_id)
            LEFT JOIN mrp_workcenter wc ON (wc.id = t.workcenter_id )
            WHERE t.workorder_id IS NOT NULL AND w.production_id = %s
            GROUP BY wc.id) a
        """
        self.env.cr.execute(query_str, (self.production_id.id, ))
        operations_cost = self.env.cr.fetchall()[0][0]

        if not operations_cost:
            # operations cost is 0 or the query returned None (no routing in BoM) - process as usual
            return res

        # search JE amount for all component of finished goods and add in the credit & debit value
        # comp_amount = 0
        # if operations_cost:
        #     query = """
        #         SELECT SUM(amount_total_signed) FROM 
        #         account_move where ref ilike %s
        #     """
        #     self.env.cr.execute(query, ("%s%s" % (self.production_id.name,'%'), ))
        #     comp_amount = self.env.cr.fetchall()[0][0]
        #     credit_value += comp_amount

        operations_cost = round(operations_cost)
        printing_cost = self._context.get('printing_cost')
        components_cost = credit_value - operations_cost - printing_cost
        # if debit_line_vals['debit']:
        #     debit_line_vals['debit'] += printing_cost
        # else:
        #     debit_line_vals['credit'] += printing_cost
        # debit_line_vals['debit'] += printing_cost# + comp_amount

        descriptions = {
            'components': _('Components: ') + description,
            'operations': _('Operations: ') + description,
            'printing': _('Printing: ') + description,
        }

        components_line_vals = {
            'name': descriptions['components'],
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': descriptions['components'],
            'partner_id': partner_id,
            'credit': components_cost,
            'debit': 0,
            'account_id': credit_account_id,
        }

        operations_line_vals = {
            'name': descriptions['operations'],
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': descriptions['operations'],
            'partner_id': partner_id,
            'credit': operations_cost,
            'debit': 0,
            'account_id': acc_src_operation_id,
        }

        printing_line_vals = {
            'name': descriptions['printing'],
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': descriptions['printing'],
            'partner_id': partner_id,
            'credit': printing_cost,
            'debit': 0,
            'account_id': acc_src_printing_id,
        }

        valuation_lines_data = {
            'components_line_vals': components_line_vals,
            'operations_line_vals': operations_line_vals,
            'printing_line_vals': printing_line_vals,
            'debit_line_vals': debit_line_vals
        }

        if 'price_diff_line_vals' in res:
            valuation_lines_data['price_diff_line_vals'] = res['price_diff_line_vals']
        return valuation_lines_data

