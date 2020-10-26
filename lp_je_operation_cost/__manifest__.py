# -*- coding: utf-8 -*-
{
    'name': "LovePop – Journal Entries for Operation Cost",
    'summary': """Makes MO's JE more detailed.""",
    'author': "Công Ty TNHH Port Cities Việt Nam",
    'website': "https://www.portcities.net",

    'category': 'Accounting',
    'version': '13.0.1.0.0',

    'depends': [
        'mrp_account',
        'stock_account',
    ],

    'data': [
        'views/stock_location_views.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}
