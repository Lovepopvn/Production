# -*- coding: utf-8 -*-
'''Product Template'''
from odoo import fields, models, _, api
from odoo.exceptions import UserError


class WorkcenterTab(models.Model):
    '''new model Workcenter Tab'''
    _name = 'workcenter.tab'
    _description = 'Workcenter Tab in Product'

    code_id = fields.Many2one('cutting.code', 'Code')
    machine_flow_id = fields.Many2one('factory.constants.lp.machine.flow', 'Machine flow')
    parallel_workcenter_id = fields.Many2one('mrp.workcenter', 'Parallel Workcenter')
    product_tmpl_id = fields.Many2one('product.template', 'Product')

class ProductTemplate(models.Model):
    '''new model product.template'''
    _inherit = 'product.template'

    production_information = fields.Boolean(related='categ_id.production_information')
    lp_height = fields.Float('Height (cm)')
    lp_length = fields.Float('Length (cm)')
    lp_width = fields.Float('Width (cm)')
    fsc_status_id = fields.Many2one(
        comodel_name='fsc.status', string='FSC Status')
    fsc_group_id = fields.Many2one(
        comodel_name='fsc.group', string='FSC Group')
    lpus_category_id = fields.Many2one(
        comodel_name='factory.constants.lpus.category', string='LPUS Category')
    lpus_product_type_id = fields.Many2one(
        comodel_name='factory.constants.lpus.product.type', string='LPUS Product Type')
    lp_batch_size = fields.Integer(string='Batch Size')
    items_per_inner_carton = fields.Integer(string='Items per Inner Carton')
    items_per_outer_carton = fields.Integer(string='Items per Outer Carton')
    carton_per_pallet = fields.Integer(string='Carton per Pallet')
    lp_sku = fields.Char(string='SKU')
    lp_upc = fields.Char(string='UPC')
    lp_unit_sku = fields.Integer(string='Units per SKU')
    lp_cpeu_value = fields.Float(string='CPEU Value')
    lp_create_date = fields.Date(string='Create Date')
    lp_sas_note = fields.Boolean(string='SAS Note')
    lp_brand_id = fields.Many2one(comodel_name='lp.product.brand', string='Lovepop Brands')
    lp_wholesale_price = fields.Float(string='Wholesale Price')
    lp_vietnam_price = fields.Float(string='Vietnam Price')
    lp_amazon_price_uk = fields.Float(string='Amazon Price - UK')
    lp_amazon_price_can = fields.Float(string='Amazon Price - CAN')
    lp_primary_vendor = fields.Char(string='Primary Vendor')
    lp_season = fields.Char(string='Season')
    lp_collection = fields.Char(string='Collection')
    lp_harmonized_code = fields.Char(
        string='Harmonized code', related='lpus_product_type_id.default_hts_code', readonly=True)
    lp_life_cycle_status = fields.Char(string='Life Cycle Status')
    lp_replenishment_status = fields.Char(string='Replenishment Status')
    lp_licensed_product = fields.Boolean(string='Licensed Product')
    lp_licensed_brand_id = fields.Many2one(
        comodel_name='licensed.brand', string='Licensed Brand')
    lp_qr_code_url = fields.Text(string='QR Code URL')
    # lp_fsc = fields.Char(string='FSC')
    routing_profile_id = fields.Many2one(
        comodel_name='routing.profile', string="Routing Profile")
    carton_type = fields.Selection([
        ('inner', 'Inner'),
        ('outer', 'Outer')
        ], string='Carton Type', copy=False)
    workcenter_tab_ids = fields.One2many(
        comodel_name='workcenter.tab', inverse_name='product_tmpl_id',
        string='Workcenter', copy=False)
    paper_description = fields.Char('Paper Description')
    number_of_inner = fields.Integer('Number of Inner')
    pallet = fields.Char('Pallet ID', copy=False)
    retail_price = fields.Float('Retail Price')
    sentiment = fields.Text('Sentiment')
    transfer_price_currency_id = fields.Many2one('res.currency', 'Transfer Price Currency')
    transfer_price = fields.Monetary(currency_field='transfer_price_currency_id')
    mfg_cost = fields.Float('MFG Cost')
    financial_model_class = fields.Char('Financial Model Class')
    brightpearl_product = fields.Boolean('Brightpearl Product')

    @api.onchange('lpus_category_id')
    def _onchange_lpus_category_id(self):
        if self.lpus_category_id:
            if self.lpus_category_id.routing_profile_id:
                self.routing_profile_id = self.lpus_category_id.routing_profile_id.id
    
    @api.onchange('lpus_product_type_id')
    def _onchange_lpus_product_type_id(self):
        if self.lpus_product_type_id:
            self.hs_code = self.lpus_product_type_id.default_hts_code

    def update_bom_packaging_routing(self):
        for prod in self:
            if not prod.default_code:
                raise UserError(_('You can only run this action if an Internal Reference is assigned'))
            packaging_data_obj = self.env['factory.constants.lp.product.packaging']
            routing_data_obj = self.env['factory.constants.lp.product.routing']
            routing_obj = self.env['mrp.routing']
            bom_obj = self.env['mrp.bom']
            # search BoM
            bom_ids = bom_obj.search([('product_tmpl_id', '=', prod.id)])
            if bom_ids:
                for bom in bom_ids:
                    bom_packaging = []
                    routing = False
                    lpus_category = prod.lpus_category_id
                    lpus_product = prod.lpus_product_type_id
                    # search data in LP Factory Constant Product Routing
                    if prod.routing_profile_id:
                        routing_data_ids = routing_data_obj.search([('routing_profile_id', '=', prod.routing_profile_id.id)],order="write_date desc", limit=1)
                    if routing_data_ids:
                        routing_name = "Routing_%s" % prod.default_code
                        # duplicate routing
                        routing = routing_data_ids.routing_id.copy({'name': routing_name})
                    # search data in LP Factory Constant Product Pckaging
                    packaging_data_ids = packaging_data_obj.search([('lpus_product_type_id', '=', lpus_product.id),
                                                                    ('lpus_category_id', '=', lpus_category.id)])
                    if packaging_data_ids:
                        for pack in packaging_data_ids:
                            vals = ((0, 0, {
                                'product_id': pack.product_id.id,
                                'quantity': pack.quantity,
                                'unit_package': pack.card_unit
                            }))
                            bom_packaging.append(vals)
                    if routing and bom_packaging:
                        if bom.packaging_data_ids:
                            bom.packaging_data_ids.unlink()
                        bom.write({
                                'packaging_data_ids': bom_packaging,
                                'routing_id': routing.id
                                })
            else:
                raise UserError(_('There is no found BoM created for this product. \n'
                                    'Please create BoM first before run this action'))
    
    def update_product_batch(self):
        for prod in self:
            packaging_data_obj = self.env['factory.constants.lp.product.packaging']
            lpus_category = prod.lpus_category_id
            lpus_product = prod.lpus_product_type_id
            packaging_data_ids = packaging_data_obj.search([('lpus_product_type_id', '=', lpus_product.id),
                                                            ('lpus_category_id', '=', lpus_category.id)])
            if packaging_data_ids:
                batch = 0
                inner_carton = 0
                for pack in packaging_data_ids:
                    if pack.product_id.carton_type == 'outer':
                        batch = pack.card_unit
                        prod.lp_batch_size = batch
                    elif pack.product_id.carton_type == 'inner':
                        inner_carton = pack.card_unit
                        prod.items_per_inner_carton = inner_carton
                if batch > 0 and inner_carton > 0:
                    prod.number_of_inner = batch / inner_carton

class ProductTemplate(models.Model):
    '''new model product.product'''
    _inherit = 'product.product'

    def _get_description(self, picking_type_id):
        """ return product receipt/delivery/picking description depending on
        picking type passed as argument.
        """
        self.ensure_one()
        picking_code = picking_type_id.code
        description = self.description or self.name
        
        if self.product_tmpl_id.fsc_group_id or self.product_tmpl_id.fsc_status_id:
            if self.product_tmpl_id.fsc_group_id and self.product_tmpl_id.fsc_status_id:
                description += ' - ' + self.product_tmpl_id.fsc_group_id.name + ' ' + self.product_tmpl_id.fsc_status_id.name
            elif self.product_tmpl_id.fsc_group_id and not self.product_tmpl_id.fsc_status_id:
                description += ' - ' + self.product_tmpl_id.fsc_group_id.name
            elif not self.product_tmpl_id.fsc_group_id and self.product_tmpl_id.fsc_status_id:
                description += ' - ' + self.product_tmpl_id.fsc_status_id.name

        if picking_code == 'incoming':
            return self.description_pickingin or description
        if picking_code == 'outgoing':
            return self.description_pickingout or description
        if picking_code == 'internal':
            return self.description_picking or description
    