{
    'name': "LovePop – COGS Reports",
    'summary': """Generates COGS reports.""",
    'author': "Công Ty TNHH Port Cities Việt Nam",
    'website': "https://www.portcities.net",

    'category': 'Accounting',
    'version': '13.0.2.0.2',

    'depends': [
        'lp_cost_recalculation',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/cogs_report_views.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}
