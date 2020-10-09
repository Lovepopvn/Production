# -*- coding: utf-8 -*-
'''Bill of Material'''
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class MrpBom(models.Model):
    '''inherit mrp.bom'''
    _inherit = 'mrp.bom'

    cutting_data_ids = fields.One2many(
        comodel_name='mrp.cutting.data', inverse_name='bom_id',
        string='Cutting Data', copy=False)
    packaging_data_ids = fields.One2many(
        comodel_name='mrp.packaging.data', inverse_name='bom_id',
        string='Packaging Data', copy=False)

    def update_production_bom(self):
        for bom in self:
            if bom.bom_line_ids:
                bom.bom_line_ids.unlink()
            packaging_data = bom.packaging_data_ids
            cutting_data = bom.cutting_data_ids
            bom_product = bom.product_tmpl_id
            component = []
            workcenter_obj = self.env['mrp.workcenter']
            rout_workcenter_obj = self.env['mrp.routing.workcenter']
            default_operation_id = False
            def_workcenter_id = workcenter_obj.search([('default_operation', '=', True)], limit=1)
            if def_workcenter_id:
                if not bom.routing_id:
                    raise UserError(_('Please set the Routing in this BoM'))
                rout_workcenter_id = rout_workcenter_obj.search([
                    ('workcenter_id', '=', def_workcenter_id.id),
                    ('routing_id', '=', bom.routing_id.id)], limit=1)
                if rout_workcenter_id:
                    default_operation_id = rout_workcenter_id.id
            for pack in packaging_data:
                # check if product already exist
                flag_product_exist = False
                for comp in component:
                    if comp[2]['product_id'] == pack.product_id.id:
                        flag_product_exist = True
                # if product does not exist on component
                if not flag_product_exist:
                    quantity = pack.quantity / pack.unit_package
                    vals = ((0, 0, {
                        'product_id': pack.product_id.id,
                        'product_qty': quantity,
                        'product_uom_id': pack.product_id.uom_id.id,
                        'operation_id': default_operation_id
                    }))
                    component.append(vals)
                # if product exist on component
                else:                   
                    for comp in component:
                        if comp[2]['product_id'] == pack.product_id.id:
                            comp[2]['product_qty'] = comp[2]['product_qty'] + (pack.quantity / pack.unit_package)
            
            # variable to create workcenter tab in product
            workcenter_tab = []
            for cut in cutting_data:
                # check if product already exist
                flag_product_exist = False
                for comp in component:
                    if comp[2]['product_id'] == cut.product_id.id:
                        flag_product_exist = True
                # if product does not exist on component
                if not flag_product_exist:
                    if cut.codes_per_sheet == 0:
                        raise UserError(_('Codes Per Sheet Should more than 0'))
                    quantity = (cut.quantity / cut.codes_per_sheet) * (1 + cut.extra_cut)
                    vals = ((0, 0, {
                        'product_id': cut.product_id.id,
                        'product_qty': quantity,
                        'product_uom_id': cut.product_id.uom_id.id,
                        'operation_id': default_operation_id
                    }))
                    component.append(vals)
                # if product exist on component
                else:                   
                    for comp in component:
                        if cut.codes_per_sheet == 0:
                            raise UserError(_('Codes Per Sheet Should more than 0'))
                        if comp[2]['product_id'] == cut.product_id.id:
                            comp[2]['product_qty'] = comp[2]['product_qty'] + ((cut.quantity / cut.codes_per_sheet) * (1 + cut.extra_cut))
                
                # prepare create workcenter constan in product
                factory_constants_obj = self.env['factory.constants']
                factory_constants_id = False
                if bom_product.lpus_product_type_id:
                    if bom_product.lpus_product_type_id.factory_constants_id:
                        factory_constants_id = bom_product.lpus_product_type_id.factory_constants_id
                if not factory_constants_id:
                    factory_constants_id = factory_constants_obj.search([], limit=1)
                if factory_constants_id:
                    workcenter_cons_obj = self.env['workcenter.constants']
                    workcenter_cons_ids = workcenter_cons_obj.search([('factory_constants_id', '=', factory_constants_id.id),
                                                                    ('machine_flow_id', '=', cut.machine_flow_id.id)])
                    # There is data for workcenter constants in factory constants
                    if workcenter_cons_ids:
                        for wc in workcenter_cons_ids:
                            data = ((0, 0, {
                                'code_id': cut.code_id.id,
                                'machine_flow_id': cut.machine_flow_id.id if cut.machine_flow_id else False,
                                'parallel_workcenter_id': wc.parallel_workcenter_id.id
                            }))
                            workcenter_tab.append(data)
                    # There is no data for workcenter constants in factory constants
                    else:
                        data = ((0, 0, {
                            'code_id': cut.code_id.id,
                            'machine_flow_id': cut.machine_flow_id.id if cut.machine_flow_id else False,
                            'parallel_workcenter_id': False
                        }))
                        workcenter_tab.append(data)
            # create workcenter tab in product
            if workcenter_tab:
                bom_product.workcenter_tab_ids.unlink()
                bom_product.write({'workcenter_tab_ids': workcenter_tab})
            bom.write({'bom_line_ids': component})
