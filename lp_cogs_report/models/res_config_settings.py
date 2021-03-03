# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    cogs_report_category_finished_id = fields.Many2one(
        'product.category', 'COGS Report Product Category for Finished Goods')
    cogs_report_category_pack_id = fields.Many2one(
        'factory.constants.lpus.category', 'COGS Report LPUS Product Category for Packs')
    cogs_report_category_raw_id = fields.Many2one(
        'product.category', 'COGS Report Product Category for Raw Material')
    cogs_report_category_sub_id = fields.Many2one(
        'product.category', 'COGS Report Product Category for Sub Material')

    cogs_report_category_finished_ids = fields.Many2many(\
        'product.category', 'finished_category_company_rel', 'company_id', 'category_id', \
            string='COGS Report Product Categories for Finished Goods')    
    cogs_report_category_pack_ids = fields.Many2many('factory.constants.lpus.category', \
        'company_lpus_category_rel', 'company_id', 'category_id', \
            string='COGS Report LPUS Product Categories for Packs')
    cogs_material_cost_account_id = fields.Many2one('account.account', \
        "Account to get Material cost")
    cogs_labor_cost_account_id = fields.Many2one('account.account', "Account to get Labor Cost")
    cogs_printing_cost_account_id = fields.Many2one('account.account', \
        "Account to get Printing Cost")
    cogs_production_location_id = fields.Many2one('stock.location', \
        "Source Location for Production")
    cogs_production_location_dest_id = fields.Many2one('stock.location', \
        "Destination Location for Production")
    cogs_location_id = fields.Many2one('stock.location', "Source Location for COGS")
    cogs_location_dest_id = fields.Many2one('stock.location', "Destination Location for COGS")
    cogs_pufp_location_id = fields.Many2one('stock.location', "Source Location for PUFP")
    cogs_pufp_location_dest_id = fields.Many2one('stock.location', "Destination Location for PUFP")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cogs_report_category_finished_id = fields.Many2one(
        'product.category', 'COGS Report Product Category for Finished Goods',
        related='company_id.cogs_report_category_finished_id', readonly=False)
    cogs_report_category_pack_id = fields.Many2one(
        'factory.constants.lpus.category', 'COGS Report LPUS Product Category for Packs',
        related='company_id.cogs_report_category_pack_id', readonly=False)
    cogs_report_category_raw_id = fields.Many2one(
        'product.category', 'COGS Report Product Category for Raw Material',
        related='company_id.cogs_report_category_raw_id', readonly=False)
    cogs_report_category_sub_id = fields.Many2one(
        'product.category', 'COGS Report Product Category for Sub Material',
        related='company_id.cogs_report_category_sub_id', readonly=False)
    
    cogs_report_category_finished_ids = fields.Many2many(
        'product.category', string='COGS Report Product Categories for Finished Goods',
        related='company_id.cogs_report_category_finished_ids', readonly=False)
    cogs_report_category_pack_ids = fields.Many2many(
        'factory.constants.lpus.category', string='COGS Report LPUS Product Categories for Packs',
        related='company_id.cogs_report_category_pack_ids', readonly=False)
    cogs_material_cost_account_id = fields.Many2one('account.account', \
        "Account to get Material cost", related='company_id.cogs_material_cost_account_id', \
            readonly=False)
    cogs_labor_cost_account_id = fields.Many2one('account.account', "Account to get Labor Cost", \
        related='company_id.cogs_labor_cost_account_id', readonly=False)
    cogs_printing_cost_account_id = fields.Many2one('account.account', \
        "Account to get Printing Cost", related='company_id.cogs_printing_cost_account_id', \
            readonly=False)
    cogs_production_location_id = fields.Many2one('stock.location', \
        "Source Location for Production", related='company_id.cogs_production_location_id', \
            readonly=False)
    cogs_production_location_dest_id = fields.Many2one('stock.location', \
        "Destination Location for Production", related='company_id.cogs_production_location_dest_id', \
            readonly=False)
    cogs_location_id = fields.Many2one('stock.location', "Source Location for COGS", \
        related='company_id.cogs_location_id', readonly=False)
    cogs_location_dest_id = fields.Many2one('stock.location', "Destination Location for COGS", \
        related='company_id.cogs_location_dest_id', readonly=False)
    cogs_pufp_location_id = fields.Many2one('stock.location', "Source Location for PUFP", \
        related='company_id.cogs_pufp_location_id', readonly=False)
    cogs_pufp_location_dest_id = fields.Many2one('stock.location', \
        "Destination Location for PUFP", related='company_id.cogs_pufp_location_dest_id', \
            readonly=False)
