# -*- coding: utf-8 -*-
'''Factory Constants'''
from odoo import fields, models


class FactoryConstants(models.Model):
    '''new model factory.constants'''
    _name = 'factory.constants'
    _description = 'Factory Constants'

    name = fields.Char(string='Factory Name', required=True)
    code = fields.Char(string='Factory Code')
    lpus_category_ids = fields.One2many(
        comodel_name='factory.constants.lpus.category', inverse_name='factory_constants_id',
        string='LPUS Category', copy=False)
    lpus_product_type_ids = fields.One2many(
        comodel_name='factory.constants.lpus.product.type', inverse_name='factory_constants_id',
        string='LPUS Product Type', copy=False)
    lp_product_packaging_ids = fields.One2many(
        comodel_name='factory.constants.lp.product.packaging', inverse_name='factory_constants_id',
        string='LP Product Packaging', copy=False)
    lp_product_routing_ids = fields.One2many(
        comodel_name='factory.constants.lp.product.routing', inverse_name='factory_constants_id',
        string='LP Product Routing', copy=False)
    carrier_id = fields.Many2one(
        comodel_name='delivery.carrier', string='Carrier/Service')
    workcenter_constants_ids = fields.One2many(
        comodel_name='workcenter.constants', inverse_name='factory_constants_id',
        string='Workcenter Constants', copy=False)
    packaging_id = fields.Many2one("product.packaging", string="Package Type")
    #Icons Left
    laser_file = fields.Binary(copy=False, string="Laser")
    laser_filename = fields.Char(copy=False, string="Laser Filename")
    die_cut_file = fields.Binary(copy=False, string="Die Cut")
    die_cut_filename = fields.Char(copy=False, string="Die Cut Filename")
    print_file = fields.Binary(copy=False, string="Print")
    print_filename = fields.Char(copy=False, string="Print Filename")
    crease_file = fields.Binary(copy=False, string="Crease")
    crease_filename = fields.Char(copy=False, string="Crease Filename")
    guillotine_file = fields.Binary(copy=False, string="Guillotine")
    guillotine_filename = fields.Char(copy=False, string="Guillotine Filename")
    foil_file = fields.Binary(copy=False, string="Foil")
    foil_filename = fields.Char(copy=False, string="Foil Filename")
    stamp_file = fields.Binary(copy=False, string="Stamp")
    stamp_filename = fields.Char(copy=False, string="Stamp Filename")
    start_time_file = fields.Binary(copy=False, string="Start Time")
    start_time_filename = fields.Char(copy=False, string="Start Time Filename")
    deadline_file = fields.Binary(copy=False, string="Deadline")
    deadline_filename = fields.Char(copy=False, string="Deadline Filename")
    urgent_file = fields.Binary(copy=False, string="Urgent")
    urgent_filename = fields.Char(copy=False, string="Urgent Filename")
    card_file = fields.Binary(copy=False, string="Card")
    card_filename = fields.Char(copy=False, string="Card Filename")
    box_file = fields.Binary(copy=False, string="Box")
    box_filename = fields.Char(copy=False, string="Box Filename")
    ship_file = fields.Binary(copy=False, string="Ship")
    ship_filename = fields.Char(copy=False, string="Ship Filename")
    airplane_file = fields.Binary(copy=False, string="Airplane")
    airplane_filename = fields.Char(copy=False, string="Airplane Filename")
    priority_file = fields.Binary(copy=False, string="Priority")
    priority_filename = fields.Char(copy=False, string="Priority Filename")
    #Icons Right
    code_of_detail_file = fields.Binary(copy=False, string="Code of Detail")
    code_of_detail_filename = fields.Char(copy=False, string="Code of Detail Filename")
    code_of_paper_file = fields.Binary(copy=False, string="Code of Paper")
    code_of_paper_filename = fields.Char(copy=False, string="Code of Paper Filename")
    paper_description_file = fields.Binary(copy=False, string="Paper Description")
    paper_description_filename = fields.Char(copy=False, string="Paper Description Filename")
    code_of_die_spec_file = fields.Binary(copy=False, string="Code of Die Spec")
    code_of_die_spec_filename = fields.Char(copy=False, string="Code of Die Spec Filename")
    cards_per_sheet_file = fields.Binary(copy=False, string="Cards per Sheet")
    cards_per_sheet_filename = fields.Char(copy=False, string="Cards per Sheet Filename")
    time_to_cut_file = fields.Binary(copy=False, string="Time to Cut")
    time_to_cut_filename = fields.Char(copy=False, string="Time to Cut Filename")
    sheets_required_file = fields.Binary(copy=False, string="Sheets Required")
    sheets_required_filename = fields.Char(copy=False, string="Sheets Required Filename")
    pieces_total_file = fields.Binary(copy=False, string="Pieces Total")
    pieces_total_filename = fields.Char(copy=False, string="Pieces Total Filename")
    sheets_in_inventory_file = fields.Binary(copy=False, string="Sheets in Inventory")
    sheets_in_inventory_filename = fields.Char(copy=False, string="Sheets in Inventory Filename")
    sheets_to_cut_file = fields.Binary(copy=False, string="Sheets to Cut")
    sheets_to_cut_filename = fields.Char(copy=False, string="Sheets to Cut Filename")
    machine_flow_file = fields.Binary(copy=False, string="Machine Flow")
    machine_flow_filename = fields.Char(copy=False, string="Machine Flow Filename")
    signature_file = fields.Binary(copy=False, string="Signature")
    signature_filename = fields.Char(copy=False, string="Signature Filename")
    code_of_packaging_file = fields.Binary(copy=False, string="Code of Packaging")
    code_of_packaging_filename = fields.Char(copy=False, string="Code of Packaging Filename")
    packaging_description_file = fields.Binary(copy=False, string="Packaging Description")
    packaging_description_filename = fields.Char(
        copy=False, string="Packaging Description Filename")
    quantity_of_packaging_file = fields.Binary(copy=False, string="Quantity of Packaging")
    quantity_of_packaging_filename = fields.Char(
        copy=False, string="Quantity of Packaging Filename")
    code_of_card_file = fields.Binary(copy=False, string="Code of Card")
    code_of_card_filename = fields.Char(copy=False, string="Code of Card Filename")
    card_description_file = fields.Binary(copy=False, string="Card Description")
    card_description_filename = fields.Char(copy=False, string="Card Description Filename")
    quantity_of_card_file = fields.Binary(copy=False, string="Quantity of Card")
    quantity_of_card_filename = fields.Char(copy=False, string="Quantity of Card Filename")
    quantity_of_stamps_file = fields.Binary(copy=False, string="Quantity of Stamps")
    quantity_of_stamps_filename = fields.Char(copy=False, string="Quantity of Stamps Filename")
    done_file = fields.Binary(copy=False, string="Done")
    done_filename = fields.Char(copy=False, string="Done Filename")
    cutting_station_file = fields.Binary(copy=False, string="Cutting Station")
    cutting_station_filename = fields.Char(copy=False, string="Cutting Station Filename")
    assembly_station_file = fields.Binary(copy=False, string="Assembly Station")
    assembly_station_filename = fields.Char(copy=False, string="Assembly Station Filename")
    quality_station_file = fields.Binary(copy=False, string="Quality Station")
    quality_station_filename = fields.Char(copy=False, string="Quality Station Filename")
    frosting_name_file = fields.Binary(copy=False, string="Frosting Name")
    frosting_name_filename = fields.Char(copy=False, string="Frosting Name Filename")
    sculpture_name_file = fields.Binary(copy=False, string="Sculpture Name")
    sculpture_name_filename = fields.Char(copy=False, string="Sculpture Name Filename")
    duplexing_file = fields.Binary(copy=False, string="Duplexing")
    duplexing_filename = fields.Char(copy=False, string="Duplexing Filename")
    lamination_file = fields.Binary(copy=False, string="Lamination")
    lamination_filename = fields.Char(copy=False, string="Lamination Filename")


class WorkcenterConstants(models.Model):
    '''new model workcenter.constants'''
    _name = 'workcenter.constants'
    _description = 'Workcenter Constants'

    factory_constants_id = fields.Many2one(
        comodel_name='factory.constants', string="Factory Constants",
        required=True, ondelete='cascade', index=True, copy=False)
    machine_flow_id = fields.Many2one(
        comodel_name='factory.constants.lp.machine.flow', string='Machine Flow')
    parallel_workcenter_id = fields.Many2one(
        comodel_name='mrp.workcenter', string='Parallel Workcenter')
    allow_produce_parallel = fields.Boolean(string='Allow to produce in parallel')
