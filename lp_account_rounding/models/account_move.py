# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    def post(self):
        # extend function post account move to create line for fixing rounding
        for move in self:
            update_ids = []
            landed_ids = []
            if not move._context.get('update_price') and ((move.stock_move_id._is_in() if move.stock_move_id else False) or not move.stock_move_id):
                for line in move.line_ids.filtered(lambda line: line.account_id.fixing_rounding):
                    diff = False
                    if line.product_id and line.account_id.fixing_rounding:
                        fix_acc = line.company_id.inventory_rounding_account_id
                        if move.stock_move_id:
                            # fix rounding for JE incoming shipment
                            valuation_a = round(line.product_id.prev_standard_price + move.amount_total_signed, 4)
                            valuation_b = round(line.product_id.qty_available * line.product_id.standard_price, 4)
                            diff = round(valuation_a-valuation_b,4)
                       
                            if diff:
                                if diff > 0:
                                    debit = line.debit - diff
                                    vals = ((1, line.id, {'debit': debit}))
                                    update_ids.append(vals)
                                    vals = ((0, 0, {
                                        'name': "Fixing Round - %s" % line.product_id.default_code, #line.name,
                                        'product_id': line.product_id.id if line.product_id else False,
                                        'quantity': line.quantity,
                                        'product_uom_id': line.product_id.uom_id.id,
                                        'ref': line.ref,
                                        'partner_id': line.partner_id.id if line.partner_id else False,
                                        'debit': diff,
                                        'credit': 0,
                                        'account_id': fix_acc.id,
                                    }))
                                    update_ids.append(vals)
                                else:
                                    debit = line.debit - diff
                                    vals = ((1, line.id, {'debit': debit}))
                                    update_ids.append(vals)
                                    vals = ((0, 0, {
                                        'name': "Fixing Round - %s" % line.product_id.default_code, #line.name,
                                        'product_id': line.product_id.id if line.product_id else False,
                                        'quantity': line.quantity,
                                        'product_uom_id': line.product_id.uom_id.id,
                                        'ref': line.ref,
                                        'partner_id': line.partner_id.id if line.partner_id else False,
                                        'debit': 0,
                                        'credit': diff * -1,
                                        'account_id': fix_acc.id,
                                    }))
                                    update_ids.append(vals)
                        else:
                            # fix rounding for JE for landed cost
                            main = [ovals for ovals in landed_ids \
                                    if ovals['product_id'] == line.product_id]
                            if main:
                                qty = main[0]['amount']
                                qty_order = line.debit
                                main[0].update({'amount': qty + qty_order})
                            else:
                                vals = {
                                    'name': line.name,
                                    'product_id': line.product_id,
                                    'quantity': line.quantity,
                                    'product_uom_id': line.product_id.uom_id.id,
                                    'ref': line.ref,
                                    'partner_id': line.partner_id,
                                    'amount': line.debit,
                                    'main_amount': line.debit,
                                    'main_id': line.id,
                                    'account_id': fix_acc.id,
                                }
                                landed_ids.append(vals)
                if landed_ids:
                    # fix rounding for JE for landed cost
                    for line in landed_ids:
                        valuation_a = round(line['product_id'].prev_standard_price + line['amount'], 4)
                        valuation_b = round(line['product_id'].qty_available * line['product_id'].standard_price, 4)
                        diff = round(valuation_a - valuation_b,4)
                        if diff:
                            if diff > 0:
                                debit = line['main_amount'] - diff
                                vals = ((1, line['main_id'], {'debit': debit}))
                                update_ids.append(vals)
                                vals = ((0, 0, {
                                    'name': "Fixing Round - %s" % line['product_id'].default_code,
                                    'product_id': line['product_id'].id if line['product_id'] else False,
                                    'quantity': line['quantity'],
                                    'product_uom_id': line['product_id'].uom_id.id,
                                    'ref': line['ref'],
                                    'partner_id': line['partner_id'].id if line['partner_id'] else False,
                                    'debit': diff,
                                    'credit': 0,
                                    'account_id': line['account_id'],
                                }))
                                update_ids.append(vals)
                            else:
                                debit = line['main_amount'] - diff
                                vals = ((1, line['main_id'], {'debit': debit}))
                                update_ids.append(vals)
                                vals = ((0, 0, {
                                    'name': "Fixing Round - %s" % line['product_id'].default_code,
                                    'product_id': line['product_id'].id if line['product_id'] else False,
                                    'quantity': line['quantity'],
                                    'product_uom_id': line['product_id'].uom_id.id,
                                    'ref': line['ref'],
                                    'partner_id': line['partner_id'].id if line['partner_id'] else False,
                                    'debit': 0,
                                    'credit': diff * -1,
                                    'account_id': line['account_id'],
                                }))
                                update_ids.append(vals)
                move.write({'line_ids': update_ids})
            return super(AccountMove, self).post()