# -*- coding: utf-8 -*-
'''Follower Sheet'''
from odoo import fields, models, _


class FollowerSheet(models.Model):
    '''new model follower.sheet'''
    _name = 'follower.sheet'
    _description = 'Folloer Sheet Manufacturing'

    code_id = fields.Many2one('cutting.code', 'code')
    product_id = fields.Many2one('product.product', 'paper')
    old_product_id = fields.Many2one('product.product', 'old paper')
    paper_description = fields.Char('Paper description')
    quantity = fields.Integer('Qty per product')
    foil_spec = fields.Char('Foil Spec')
    cards_per_sheet = fields.Integer('Cards per Sheet')
    machine_flow_id = fields.Many2one(
        comodel_name='factory.constants.lp.machine.flow', string='Machine Flow')
    pieces_total = fields.Integer('Pieces Total')
    pieces_required = fields.Integer('Pieces Required')
    extra_cut = fields.Float('Extra Cut')
    sheets_required = fields.Float('Sheets Require')
    sheets_inventory = fields.Float('Sheets in Inventory')
    sheets_cut = fields.Float('Sheets to Cut')
    number_printed_side = fields.Integer('Printed Sides No.')
    total_printed_side = fields.Integer('Total Printed Sides')
    mo_id = fields.Many2one('mrp.production', 'Manufacturing Order')
    additional_material = fields.Char('Additional Material')

    def write(self, values):
        for follower in self:
            if values.get('product_id'):
                follower.old_product_id = follower.product_id.id
        res = super(FollowerSheet, self).write(values)
        for follower in self:
            if values.get('product_id'):
                follower.paper_description = follower.product_id.paper_description
        return res
