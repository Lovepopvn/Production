# -*- coding: utf-8 -*-
{
    'name': "LovePop – Click Charge Management in MO",
    'summary': """Adds Cost of Printing to MO Cost Analysis.""",
    'author': "Công Ty TNHH Port Cities Việt Nam",
    'website': "https://www.portcities.net",

    'category': 'Accounting',
    'version': '13.0.1.0.0',

    'depends': [
        'lp_mrp',
        'mrp_account_enterprise',
    ],

    'data': [
        'views/cost_structure_report.xml',
        'views/factory_constants_views.xml',
        'views/mrp_production_view.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}
