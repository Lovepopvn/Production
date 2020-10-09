# coding: utf-8

{
    'name': 'LovePop – Transfer Price Update',
    'summary': "Daily updates products' Transfer Price from selected Pricelist",
    'author': 'Công Ty TNHH Port Cities Việt Nam',
    'website': 'https://www.portcities.net',

    'category': 'Manufacturing',
    'version': '13.0.1.0',
    'sequence': 1,

    'depends': [
        'lp_mrp',
        'sale',
        'product',
    ],

    'data': [
        'views/res_config_settings_views.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False
}
