# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Custom Manufacturing LovePop',
    'version': '13.0.1.1.6',
    'category': 'Manufacturing',
    'summary': 'Custom Manufacturing process',
    'description': """
    v.13.0.1.1.1 \n
    - Fix paper shipping label \n
    v.13.0.1.1.2 \n
    - Fix MO production document \n
    v.13.0.1.1.3 \n
    - Fix issue when pause item didn't yet end, WO should be can't done \n
    v.13.0.1.1.4 \n
    - update commercial invoice and AWB Fedex \n
    """,
    'website': 'https://www.portcities.net',
    'author': 'Portcities Ltd.',
    'images': [],
    'depends': ['mrp', 'sale', 'purchase', 'delivery_fedex', 'barcodes'],
    'data': [
        'security/ir.model.access.csv',
        'data/data_sequence.xml',
        'data/scheduler_data.xml',
        'wizard/cancel_so_wizard_view.xml',
        'wizard/mo_divisible_confirmation_view.xml',
        'wizard/do_remove_wave_view.xml',
        'wizard/mrp_workorder_pause_reason_view.xml',
        'views/sale_order_view.xml',
        'views/routing_profile_view.xml',
        'views/cutting_code_view.xml',
        'views/fsc_data_view.xml',
        'views/licensed_brand_view.xml',
        'views/order_type_view.xml',
        'views/factory_constants_lpus_category_view.xml',
        'views/factory_constants_lpus_product_type_view.xml',
        'views/factory_constants_lp_product_packaging_view.xml',
        'views/factory_constants_lp_product_routing_view.xml',
        'views/factory_constants_lp_machine_flow_view.xml',
        'views/factory_constants_view.xml',
        'views/res_company_view.xml',
        'views/product_category_view.xml',
        'views/product_view.xml',
        'views/mrp_bom_view.xml',
        'views/mrp_packaging_data_view.xml',
        'views/mrp_cutting_data_view.xml',
        'views/product_lot_view.xml',
        'views/mrp_workcenter_view.xml',
        'views/mrp_production_view.xml',
        'views/stock_inventory_views.xml',
        'views/picking_wave_views.xml',
        'views/res_config_setting_view.xml',
        'views/mrp_workorder_view.xml',
        'views/delivery_carrier_view.xml',
        'report/production_report.xml',
        'report/production_label_report.xml',
        'report/mrp_production_templates.xml',
        'report/report_stockpicking_templates.xml',
        'static/src/xml/templates.xml',
    ],
    'qweb': [
        'static/src/xml/stock_barcode.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
