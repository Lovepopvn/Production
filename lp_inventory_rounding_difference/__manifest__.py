# -*- coding: utf-8 -*-
{
    'name': "LovePop – Inventory Rounding Difference",
    'summary': """Rounds product cost after AVCO valuation""",
    'author': "Công Ty TNHH Port Cities Việt Nam",
    'website': "https://www.portcities.net",

    'category': 'Accounting',
    'version': '13.0.1.0.0',

    'depends': [
        'stock_account',
    ],

    'data': [
        'views/res_config_settings_views.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}
