{
    'name': "LovePop – Asset Information",
    'summary': """Adds extra fields to Asset.""",
    'author': "Công Ty TNHH Port Cities Việt Nam",
    'website': "https://www.portcities.net",

    'category': 'Accounting',
    'version': '13.0.1.0.0',

    'depends': [
        'account_asset',
    ],

    'data': [
        'views/account_asset_views.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}
