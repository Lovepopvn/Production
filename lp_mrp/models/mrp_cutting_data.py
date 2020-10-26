# -*- coding: utf-8 -*-
'''Cutting Data BoM'''
from odoo import fields, models, api, _


class MrpCuttingData(models.Model):
    '''new model mrp.cutting.data'''
    _name = 'mrp.cutting.data'
    _description = 'Bom Cutting Data'

    bom_id = fields.Many2one('mrp.bom', 'Bill of Material')
    code_id = fields.Many2one('cutting.code', 'Code')
    product_id = fields.Many2one('product.product', 'Product') 
    paper_description = fields.Char('Paper description')
    quantity = fields.Integer('Qty per product', default=1)
    codes_per_sheet = fields.Integer('Codes per Sheet')
    extra_cut = fields.Float('Extra cut', default=0.01)
    machine_flow_id = fields.Many2one('factory.constants.lp.machine.flow', 'Machine flow')
    number_printed_side = fields.Integer('Printed Sides No.')
    additional_material = fields.Char('Additional Material')

    def name_get(self):
        result = []
        for cut in self:
            if cut.product_id:
                result.append((cut.id, _("[%s] %s")%(cut.code_id.name, cut.product_id.name)))
            else:
                result.append((cut.id, _("%s")%(cut.code_id.name)))
        return result

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            # desc = "%s" % self.product_id.name
            if self.product_id.paper_description:
                self.paper_description = self.product_id.paper_description
            else:
                self.paper_description = False
            #     desc = "[%s] %s" % (self.product_id.default_code, desc)
            # if self.product_id.fsc_status_id and not self.product_id.fsc_group_id:
            #     desc = "%s - %s" % (desc, self.product_id.fsc_status_id.name)
            # elif self.product_id.fsc_group_id and not self.product_id.fsc_status_id:
            #     desc = "%s - %s" % (desc, self.product_id.fsc_group_id.name)
            # elif self.product_id.fsc_status_id and self.product_id.fsc_group_id:
            #     desc = "%s - %s %s" % (desc,self.product_id.fsc_status_id.name,self.product_id.fsc_group_id.name)
            # self.paper_description = desc
