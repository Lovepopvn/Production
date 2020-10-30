# -*- coding: utf-8 -*-
{
    'name': "LovePop – Aged Forward Reports",
    'summary': """Adds Aged Forward Reports to the Partner Reports menu of Accounting.""",
    'author': "Công Ty TNHH Port Cities Việt Nam",
    'website': "https://www.portcities.net",

    'category': 'Accounting',
    'version': '13.0.1.0.0',

    'depends': [
        'account_reports',
    ],

    'data': [
        'views/account_financial_report_views.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}
