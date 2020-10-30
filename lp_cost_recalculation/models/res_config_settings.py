# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    cogs_allocation_valuation_account_id = fields.Many2one(
        'account.account', 'COGS Allocation Valuation Account')
    cogs_allocation_counterpart_account_material_loss_id = fields.Many2one(
        'account.account', 'COGS Allocation Counterpart Account For Material Loss')
    cogs_allocation_counterpart_account_direct_labor_id = fields.Many2one(
        'account.account', 'COGS Allocation Counterpart Account For Direct Labor')
    cogs_allocation_counterpart_account_overhead_cost_id = fields.Many2one(
        'account.account', 'COGS Allocation Counterpart Account For Overhead Cost')
    cogs_allocation_counterpart_account_click_charge_id = fields.Many2one(
        'account.account', 'COGS Allocation Counterpart Account For Click Charge')

    # make_to_stock_allocation_valuation_account_id = fields.Many2one(
    #     'account.account', 'Make To Stock Allocation Valuation Account')
    make_to_stock_allocation_counterpart_account_material_loss_id = fields.Many2one(
        'account.account', 'Make To Stock Allocation Counterpart Account For Material Loss')
    make_to_stock_allocation_counterpart_account_direct_labor_id = fields.Many2one(
        'account.account', 'Make To Stock Allocation Counterpart Account For Direct Labor')
    make_to_stock_allocation_counterpart_account_overhead_cost_id = fields.Many2one(
        'account.account', 'Make To Stock Allocation Counterpart Account For Overhead Cost')
    make_to_stock_allocation_counterpart_account_click_charge_id = fields.Many2one(
        'account.account', 'Make To Stock Allocation Counterpart Account For Click Charge')

    wip_pack_allocation_counterpart_account_material_loss_id = fields.Many2one(
        'account.account', 'WIP Pack Allocation Counterpart Account For Material Loss')
    wip_pack_allocation_counterpart_account_direct_labor_id = fields.Many2one(
        'account.account', 'WIP Pack Allocation Counterpart Account For Direct Labor')
    wip_pack_allocation_counterpart_account_overhead_cost_id = fields.Many2one(
        'account.account', 'WIP Pack Allocation Counterpart Account For Overhead Cost')
    wip_pack_allocation_counterpart_account_click_charge_id = fields.Many2one(
        'account.account', 'WIP Pack Allocation Counterpart Account For Click Charge')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cogs_allocation_valuation_account_id = fields.Many2one(
        'account.account', 'COGS Allocation Valuation Account',
        related='company_id.cogs_allocation_valuation_account_id', readonly=False)
    cogs_allocation_counterpart_account_material_loss_id = fields.Many2one(
        'account.account', 'COGS Allocation Counterpart Account For Material Loss',
        related='company_id.cogs_allocation_counterpart_account_material_loss_id', readonly=False)
    cogs_allocation_counterpart_account_direct_labor_id = fields.Many2one(
        'account.account', 'COGS Allocation Counterpart Account For Direct Labor',
        related='company_id.cogs_allocation_counterpart_account_direct_labor_id', readonly=False)
    cogs_allocation_counterpart_account_overhead_cost_id = fields.Many2one(
        'account.account', 'COGS Allocation Counterpart Account For Overhead Cost',
        related='company_id.cogs_allocation_counterpart_account_overhead_cost_id', readonly=False)
    cogs_allocation_counterpart_account_click_charge_id = fields.Many2one(
        'account.account', 'COGS Allocation Counterpart Account For Click Charge',
        related='company_id.cogs_allocation_counterpart_account_click_charge_id', readonly=False)

    # make_to_stock_allocation_valuation_account_id = fields.Many2one(
    #     'account.account', 'Make To Stock Allocation Valuation Account',
    #     related='company_id.make_to_stock_allocation_valuation_account_id',
    #     readonly=False)
    make_to_stock_allocation_counterpart_account_material_loss_id = fields.Many2one(
        'account.account', 'Make To Stock Allocation Counterpart Account For Material Loss',
        related='company_id.make_to_stock_allocation_counterpart_account_material_loss_id',
        readonly=False)
    make_to_stock_allocation_counterpart_account_direct_labor_id = fields.Many2one(
        'account.account', 'Make To Stock Allocation Counterpart Account For Direct Labor',
        related='company_id.make_to_stock_allocation_counterpart_account_direct_labor_id',
        readonly=False)
    make_to_stock_allocation_counterpart_account_overhead_cost_id = fields.Many2one(
        'account.account', 'Make To Stock Allocation Counterpart Account For Overhead Cost',
        related='company_id.make_to_stock_allocation_counterpart_account_overhead_cost_id',
        readonly=False)
    make_to_stock_allocation_counterpart_account_click_charge_id = fields.Many2one(
        'account.account', 'Make To Stock Allocation Counterpart Account For Click Charge',
        related='company_id.make_to_stock_allocation_counterpart_account_click_charge_id',
        readonly=False)

    wip_pack_allocation_counterpart_account_material_loss_id = fields.Many2one(
        'account.account', 'WIP Pack Allocation Counterpart Account For Material Loss',
        related='company_id.wip_pack_allocation_counterpart_account_material_loss_id', readonly=False)
    wip_pack_allocation_counterpart_account_direct_labor_id = fields.Many2one(
        'account.account', 'WIP Pack Allocation Counterpart Account For Direct Labor',
        related='company_id.wip_pack_allocation_counterpart_account_direct_labor_id', readonly=False)
    wip_pack_allocation_counterpart_account_overhead_cost_id = fields.Many2one(
        'account.account', 'WIP Pack Allocation Counterpart Account For Overhead Cost',
        related='company_id.wip_pack_allocation_counterpart_account_overhead_cost_id', readonly=False)
    wip_pack_allocation_counterpart_account_click_charge_id = fields.Many2one(
        'account.account', 'WIP Pack Allocation Counterpart Account For Click Charge',
        related='company_id.wip_pack_allocation_counterpart_account_click_charge_id', readonly=False)
