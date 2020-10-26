# -*- coding: utf-8 -*-
'''Manufacturing Order'''
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import math


class MrpProduction(models.Model):
    '''inherit mrp.production'''
    _name = 'mrp.production'
    _inherit = ['mrp.production', 'barcodes.barcode_events_mixin']
    _description = 'Manufacturing Order'

    sale_id = fields.Many2one('sale.order', 'Sale Order', copy=False)
    urgency = fields.Selection([
        ('very_urgent', 'Very Urgent'),
        ('urgent', 'Urgent'),
        ('priority', 'Priority'),
        ('standard', 'Standard')
        ], string='Urgency', copy=False)
    follower_sheets_ids = fields.One2many(
        comodel_name='follower.sheet', inverse_name='mo_id',
        string='Follower Sheets', copy=False)
    product_lot_ids = fields.One2many(
        comodel_name='product.lot', inverse_name='mo_id',
        string='Packaging Definition', copy=False)
    parent_mo_id = fields.Many2one('mrp.production','Parent MO')
    mo_for_samples = fields.Boolean('MO for Samples')
    expected_ship_date = fields.Datetime('Expected Ship Date')

    def button_plan(self):
        for order in self:
            if not all(line.product_uom_qty == line.reserved_availability for line in order.move_raw_ids.filtered(
                    lambda x: x.product_id.categ_id.require_for_mo == True)):
                raise UserError(_('To consume & Reserver should be same for specific product category'))
            # if all(line.statement_id for line in line.payment_id.move_line_ids.filtered(
            #             lambda r: r.id != line.id and r.account_id.internal_type == 'liquidity')):
        res = super(MrpProduction, self).button_plan()
        for order in self:
            if order.expected_ship_date: 
                order.sale_id.commitment_date = order.expected_ship_date
                order.product_lot_ids.write({'do_ship_date': order.expected_ship_date})
                order.sale_id.picking_ids.write({'scheduled_date': order.expected_ship_date})
        return res

    def create_initial_follower_sheet(self):
        for mo in self:
            if mo.bom_id: 
                bom = mo.bom_id
                follower_sheet_obj = self.env['follower.sheet']
                follower_sheet = []
                mo_qty = mo.product_qty
                for cut in bom.cutting_data_ids:
                    pieces_total = math.ceil((mo_qty * (1 + cut.extra_cut)))
                    pieces_required = cut.quantity * mo_qty
                    if cut.codes_per_sheet == 0:
                        raise UserError(_('Cards per Sheet in cutting data pf BoM can not be 0'))
                    sheets_required = math.ceil((pieces_required / cut.codes_per_sheet) * (1 + cut.extra_cut))
                    # sheets_inventory = cut.product_id.qty_available
                    # sheets_cut = sheets_required
                    total_printed_side = sheets_required * cut.number_printed_side
                    vals = ((0, 0, {
                        'code_id': cut.code_id.id,
                        'product_id': cut.product_id.id,
                        'paper_description': cut.paper_description,
                        'quantity': cut.quantity,
                        'foil_spec': '',
                        'additional_material': cut.additional_material,
                        'cards_per_sheet': cut.codes_per_sheet,
                        'machine_flow_id': cut.machine_flow_id.id,
                        'pieces_total': pieces_total,
                        'pieces_required': pieces_required,
                        'extra_cut': cut.extra_cut,
                        'sheets_required': sheets_required,
                        # 'sheets_inventory': sheets_inventory,
                        # 'sheets_cut': sheets_cut,
                        'number_printed_side': cut.number_printed_side,
                        'total_printed_side': total_printed_side,
                    }))
                    follower_sheet.append(vals)
                if mo.follower_sheets_ids:
                    mo.follower_sheets_ids.unlink()
                mo.write({'follower_sheets_ids': follower_sheet})
    
    def correct_consumed_paper_of_the_manufacturing_order(self):
        StockMove = self.env['stock.move']
        FollowerSheet = self.env['follower.sheet']
        for mo in self:
            wo_id = self.env['mrp.workorder'].search([('production_id', '=', mo.id), ('workcenter_id.default_operation_pick', '=', True), ('state', 'not in', ['done', 'cancel'])])
            if not wo_id:
                raise UserError("Pick Paper not available")
            
            # IF PRODUCT FOLLOWER CHANGED
            sql_old_product = """
                SELECT product_id, old_product_id, sheets_required FROM follower_sheet WHERE mo_id = %s AND old_product_id IS NOT NULL GROUP BY product_id, old_product_id, sheets_required
            """
            self.env.cr.execute(sql_old_product, (mo.id, ))
            follower_sheet = self.env.cr.fetchall()
            if follower_sheet:
                for follower in follower_sheet:
                    sql_old = """
                        SELECT product_id, sheets_required FROM follower_sheet WHERE mo_id = %s AND old_product_id = %s GROUP BY product_id, old_product_id, sheets_required
                    """
                    self.env.cr.execute(sql_old, (mo.id, follower[1]))
                    old_follower = self.env.cr.fetchall()

                    sql_all = """
                        SELECT product_id, sheets_required FROM follower_sheet WHERE mo_id = %s AND product_id = %s GROUP BY product_id, old_product_id, sheets_required
                    """
                    self.env.cr.execute(sql_all, (mo.id, follower[1]))
                    all_follower = self.env.cr.fetchall()
                    if old_follower and all_follower:
                        followers = mo.follower_sheets_ids.filtered(lambda x: x.product_id.id == follower[1])
                        qty = sum([follow['sheets_required'] for follow in followers])
                        move_id = StockMove.search([('product_id', '=', follower[1]), ('raw_material_production_id', '=', mo.id)])
                        if move_id:
                            move_id.write({
                                'unit_factor': qty / mo.product_qty,
                                'product_uom_qty': qty,
                            })
                        
                        move_id = StockMove.search([('product_id', '=', follower[0]), ('raw_material_production_id', '=', mo.id)])
                        if move_id:
                            followers2 = mo.follower_sheets_ids.filtered(lambda x: x.product_id.id == follower[0])
                            qty2 = sum([foll['sheets_required'] for foll in followers2])
                            move_id.write({
                                'unit_factor': qty2 / mo.product_qty,
                                'product_uom_qty': qty2,
                            })
                        else:
                            product_id = self.env['product.product'].search([('id', '=', follower[0])])
                            LocationDest = product_id.with_context(force_company=self.company_id.id).property_stock_production
                            new_move = StockMove.create({
                                'name': mo.name,
                                'product_id': product_id.id,
                                'unit_factor': follower[2] / mo.product_qty,
                                'product_uom_qty': follower[2],
                                'product_uom': product_id.uom_id.id,
                                'location_id': mo.location_src_id.id,
                                'location_dest_id': LocationDest.id,
                                'raw_material_production_id': mo.id,
                                'sequence': 1,
                                'price_unit': product_id.standard_price,
                                'origin': mo.name,
                                'picking_type_id': mo.picking_type_id.id,
                                'group_id': mo.procurement_group_id.id,
                                'workorder_id': wo_id.id,
                            })
                            new_move._action_confirm()
                    elif old_follower and not all_follower:
                        move_id = StockMove.search([('product_id', '=', follower[0]), ('raw_material_production_id', '=', mo.id)])
                        if move_id:
                            followers2 = mo.follower_sheets_ids.filtered(lambda x: x.product_id.id == follower[0])
                            qty2 = sum([foll['sheets_required'] for foll in followers2])
                            move_id.write({
                                'unit_factor': qty2 / mo.product_qty,
                                'product_uom_qty': qty2,
                            })
                        else:
                            moves_id = StockMove.search([('product_id', '=', follower[1]), ('raw_material_production_id', '=', mo.id)])
                            if moves_id:
                                followers1 = mo.follower_sheets_ids.filtered(lambda x: x.product_id.id == follower[0])
                                qtys = sum([follo['sheets_required'] for follo in followers1])
                                moves_id._do_unreserve()
                                moves_id.write({
                                    'product_id': follower[0],
                                    'unit_factor': qtys / mo.product_qty,
                                    'product_uom_qty': qtys
                                })
                            else:
                                product_id = self.env['product.product'].search([('id', '=', follower[0])])
                                LocationDest = self.env['stock.location'].search([('usage', '=', 'production')])
                                new_move = StockMove.create({
                                    'name': mo.name,
                                    'product_id': product_id.id,
                                    'unit_factor': follower[2] / mo.product_qty,
                                    'product_uom_qty': follower[2],
                                    'product_uom': product_id.uom_id.id,
                                    'location_id': mo.location_src_id.id,
                                    'location_dest_id': LocationDest.id,
                                    'raw_material_production_id': mo.id,
                                    'sequence': 1,
                                    'price_unit': product_id.standard_price,
                                    'origin': mo.name,
                                    'picking_type_id': mo.picking_type_id.id,
                                    'group_id': mo.procurement_group_id.id,
                                    'workorder_id': wo_id.id,
                                })
                                new_move._action_confirm()
                    sql_check_follower = """
                        SELECT product_id, sheets_required FROM follower_sheet WHERE mo_id = %s AND product_id = %s GROUP BY product_id, old_product_id, sheets_required
                    """
                    self.env.cr.execute(sql_check_follower, (mo.id, follower[1]))
                    check_follower = self.env.cr.fetchall()
                    if not check_follower:
                        unlink_move = StockMove.search([('product_id', '=', follower[1]), ('raw_material_production_id', '=', mo.id)])
                        if unlink_move:
                            unlink_move._do_unreserve()
                            unlink_move._action_cancel()
                            unlink_move.unlink()
            WorkOrderLine = self.env['mrp.workorder.line']
            workorder_id = self.env['mrp.workorder'].search([('production_id', '=', mo.id), ('workcenter_id.default_operation_pick', '=', True)])
            if workorder_id:
                move_lines = []
                workorder_lines = []
                data_stock_move = StockMove.search([('raw_material_production_id', '=', mo.id)])
                
                for stock_moveline in data_stock_move:
                    move_lines.append(stock_moveline.product_id.id)
                
                data_workorder_line = WorkOrderLine.search([('raw_workorder_id', '=', workorder_id.id)])
                for lines in data_workorder_line:
                    if lines.product_id.id in move_lines:
                        stock_move = StockMove.search([('product_id', '=', lines.product_id.id), ('raw_material_production_id', '=', mo.id)])
                        lines.write({
                            'qty_to_consume': stock_move.product_uom_qty,
                            'move_id': stock_move.id
                        })
                        workorder_lines.append(lines.product_id.id)
                    else:
                        lines.unlink()
                
                for stock_moveline in data_stock_move:
                    if stock_moveline.product_id.id not in workorder_lines:
                        WorkOrderLine.create({
                            'raw_workorder_id': workorder_id.id,
                            'move_id': stock_moveline.id,
                            'product_id': stock_moveline.product_id.id,
                            'qty_to_consume': stock_moveline.product_uom_qty,
                            'qty_reserved': stock_moveline.product_uom_qty,
                            'product_uom_id': stock_moveline.product_uom.id,
                            'qty_done': stock_moveline.product_uom_qty,
                        })

                self.env.cr.execute("""
                    SELECT product_id, COUNT(*) FROM mrp_workorder_line WHERE raw_workorder_id = %s GROUP BY product_id HAVING COUNT(*) > 1
                """, (workorder_id.id, ))
                double_workorder = self.env.cr.fetchall()
                if double_workorder:
                    for doub in double_workorder:
                        b = 0
                        work_line = WorkOrderLine.search([('product_id', '=', doub[0]), ('raw_workorder_id', '=', workorder_id.id)])
                        if len(work_line) > 1:
                            while b < len(work_line)-1:
                                work_line[b].unlink()
                                b += 1
            mo.follower_sheets_ids.write({'old_product_id': False})

    def change_products(self, id, product_id):
        for line in self.follower_sheets_ids:
            if line.id == id:
                move_id = self.env['stock.move'].search([('product_id', '=', line.product_id.id), ('raw_material_production_id', '=', self.id)])
                product_id = self.env['product.product'].search([('id', '=', product_id)])
                if line.product_id.uom_id.id != product_id.uom_id.id:
                    raise UserError('Product UoM not same, please check Product UoM First')
                move_id.write({
                    'product_id': product_id.id,
                    'product_uom': product_id.uom_id.id
                })

    def action_confirm(self):
        for mo in self:
            for move in mo.move_raw_ids:
                decimal = move.product_uom_qty % 1
                if decimal > 0.1:
                    move.product_uom_qty = math.ceil(move.product_uom_qty)
                else:
                    move.product_uom_qty = math.floor(move.product_uom_qty)
            # FRD 7
            if mo.product_id.lpus_product_type_id.allow_proceed_remove and mo.parent_mo_id:
                lpus_product_type = mo.product_id.lpus_product_type_id
                lpus_category = mo.product_id.lpus_category_id
                lpus_product_package = self.env['factory.constants.lp.product.packaging'].search([('packaging_data_removable', '=', True), 
                                                                                                  ('lpus_product_type_id', '=', lpus_product_type.id),
                                                                                                  ('lpus_category_id', '=', lpus_category.id)])
                product_package = []
                for package in lpus_product_package:
                    if package.product_id.id not in product_package:
                        product_package.append(package.product_id.id)
                for material in mo.move_raw_ids:
                    if material.product_id.id in product_package:
                        material.unlink()
       
        res = super(MrpProduction, self).action_confirm()
        for mo in self:
            sale_id = self.env['sale.order'].search([('name', '=', mo.origin)], limit=1)
            if sale_id:
                so_line = self.env['sale.order.line'].search([('order_id', '=', sale_id.id),
                                                            ('product_id', '=', mo.product_id.id)],
                                                            limit=1)
                mo_qty = mo.product_qty
                batch_size = mo.product_id.lp_batch_size
                # if mo_qty < batch_size:
                #     raise UserError(_('Manufacturing Order Quantity can not less than Batch Size'))
                tot_product_lot = math.ceil(mo_qty / batch_size)
                tot_sequence = tot_product_lot
                seq = 1
                tot_item = mo_qty
                product_weight = mo.product_id.weight
                loaded_length = 0
                loaded_width = 0
                loaded_height = 0
                inner_carton_weight = 0
                inner_carton_qty = 0
                outer_carton_weight = 0
                outer_carton_qty = 0
                for material in mo.move_raw_ids:
                    if material.product_id.carton_type == 'inner':
                        inner_carton_weight += material.product_id.weight
                        inner_carton_qty += material.product_uom_qty
                    if material.product_id.carton_type == 'outer':
                        outer_carton_weight += material.product_id.weight
                        outer_carton_qty += material.product_uom_qty
                        loaded_length += material.product_id.lp_length
                        loaded_width += material.product_id.lp_width
                        loaded_height += material.product_id.lp_height
                while tot_product_lot > 0:
                    lot_name = self.env['ir.sequence'].next_by_code('product.lot') or '/'
                    delivery_order = self.env['stock.picking'].search([('sale_id', '=', sale_id.id)],limit=1)
                    number_of_item = batch_size
                    if tot_item < batch_size:
                        number_of_item = tot_item
                    ''' (loaded_container_weight =  Unit weight of Product x Number of Items in Product Lot) +  
                        (weight of inner carton (material where carton_type = inner)  x  qty of inner carton (in packaging data)) +
                        (weight of outer carton (material where carton_type = outer))'''
                    mo_product_weight_cal = (product_weight*number_of_item)
                    inner_weight_cal = (inner_carton_weight*inner_carton_qty)
                    outer_weight_cal = (outer_carton_weight)
                    loaded_container_weight = mo_product_weight_cal + inner_weight_cal + outer_weight_cal
                    carrier = False
                    package_type = False
                    factory_constants = mo.company_id.factory_constants_id
                    if sale_id.shipment_method == 'AIR' and factory_constants:
                        if factory_constants.carrier_id:
                            carrier = factory_constants.carrier_id.id
                    if factory_constants:
                        if factory_constants.packaging_id:
                            package_type = factory_constants.packaging_id.id
                    vals = ({
                            'name': lot_name,
                            'state': 'not_received',
                            'delivery_order_id':delivery_order.id ,
                            'mo_id': mo.id,
                            'product_id': mo.product_id.id,
                            # 'expected_delivery_date': delivery_order.scheduled_date,
                            'tracking_number': '',
                            'tracking_link': '',
                            'picking_wave_id': False,
                            'do_ship_date': delivery_order.scheduled_date,
                            'number_of_items': number_of_item,
                            'number_of_inner': mo.product_id.number_of_inner,
                            'inner_per_outer': mo.product_id.items_per_outer_carton,
                            'items_per_inner_carton': mo.product_id.items_per_inner_carton,
                            'sequence_number': seq,
                            'sequence_total': tot_sequence,
                            'unit_weight': product_weight,
                            'unit_price': so_line.price_unit,
                            'loaded_container_length': loaded_length,
                            'loaded_container_width': loaded_width,
                            'loaded_container_height': loaded_height,
                            'loaded_container_weight': loaded_container_weight,
                            'scanning_order': 0,
                            'inner_type': 'standard',
                            'received': 0,
                            'urgency': sale_id.urgency,
                            'shipment_method': sale_id.shipment_method,
                            'carrier_id': carrier,
                            'packaging_id': package_type,
                            'so_number': sale_id.name,
                            'brightpearl_warehouse_id': sale_id.brightpearl_warehouse_id,
                            'pallet': mo.product_id.pallet,
                            'partner_id': sale_id.partner_id.id,
                            'mo_for_samples': mo.mo_for_samples,
                            })
                    seq += 1
                    tot_item = tot_item - batch_size
                    tot_product_lot = tot_product_lot - 1
                    self.env['product.lot'].create(vals)
        return res

    @api.model
    def create(self, values):
        if values.get('origin'):
            data_mo = self.search([('name', 'ilike', values.get('origin'))], limit=1)
            if data_mo:
                values['parent_mo_id'] = data_mo.id
        return super(MrpProduction, self).create(values)

    def get_separated_product_lot_ids(self):
        self.ensure_one()
        list_lot = []
        i = 0
        for l in self.product_lot_ids:
            if not list_lot:
                list_lot.append(l)
                continue
            len_list_lot = len(list_lot)
            if len_list_lot >= i+1 and len(list_lot[i]) == 1:
                list_lot[i] |= l
                i += 1
            else:
                list_lot.append(l)
        return list_lot

    def check_product_packaging_bom(self, bom_id, product):
        packaging_data_from_bom = self.env['mrp.packaging.data'].search([('bom_id', '=', bom_id.id)])
        for data in packaging_data_from_bom:
            if product.id == data.product_id.id:
                return True
