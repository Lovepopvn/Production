# -*- coding: utf-8 -*-
{
    'name': "LovePop – Product Cost Recalculation",
    'summary': """Allows monthly recalculation of products' manufacturing costs.""",
    'author': "Công Ty TNHH Port Cities Việt Nam",
    'website': "https://www.portcities.net",

    'category': 'Accounting',
    'version': '13.0.1.4.0',

    'depends': [
        'account',
        'account_accountant',
        'product',
        'stock',
        'mrp',
        'stock_account',
        'lp_mrp',
        'lp_click_charge_mo',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/cost_recalculation_views.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}
