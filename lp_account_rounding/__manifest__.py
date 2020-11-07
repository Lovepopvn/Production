# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Account Fix Rounding',
    'version': '13.0.1.0.1',
    'category': 'Account',
    'summary': 'Account for fixing rounding issue in cost valuation & Journal Entries',
    'description': """
        Add new journal item to fix Gap amount between JE and Cost Valuation product \n
        v.13.0.1.0.1 \n
    - Fix fixing rounding function only for receipt product and finished product of MO \n
    """,
    'website': 'https://www.portcities.net',
    'author': 'Portcities Ltd.',
    'depends': ['stock_landed_costs'],
    'data': [
        'views/account_account_views.xml',
        'views/res_config_settings_views.xml',
        "views/product_views.xml"
    ],
    'installable': True,
    'auto_install': False,
    'application': False
}
