{
    'name': "LovePop – Budget Report (Excel)",
    'summary': """Generates XLSX Budget report.""",
    'author': "Công Ty TNHH Port Cities Việt Nam",
    'website': "https://www.portcities.net",

    'category': 'Accounting',
    'version': '13.0.1.0.0',

    'depends': [
        'mrp',
        'stock_account',
        'account_account_english',
    ],

    'data': [
        'wizard/budget_report_views.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}
