{
    'name': 'Vietnam - Generate Excel Journal Legder',
    'version': '13.0.1.0.0',
    'summary': 'Additional feature for vietnamese journal ledger',
    'description': """
        Add wizard to generate excel Journal Ledger
    """,
    'category': 'Accounting',
    'author': 'Portcities Ltd',
    'website': 'https://portcities.net',
    'depends': [
        'account',
        'to_account_counterpart',
        'account_account_english'
    ],
    'data': [
        'wizard/wizard_generate_journal_ledger_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
