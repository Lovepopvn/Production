
{
    'name': 'Vietnam - Accounting VAS Report',
    'version': '13.0.1.0.0',
    'summary': 'Additional feature VAS report for vietnamese accounting standard',
    'description': """
- Profit Loss
- Balance Sheet
- Indirect Cash Flow
    """,
    'category': 'Accounting',
    'author': 'Portcities Ltd',
    'website': 'https://portcities.net',
    'depends': [
        'account_reports','account_account_english',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/account_type.xml',
        # 'data/account.account.csv',
        'data/account_journal.xml',
        'data/account_financial_report_bs_b01_data.xml',
        'data/account_financial_report_pnl_b02_data.xml',
        'data/account_financial_report_icf_b03_data.xml',
        'data/account.activity.csv',
        'data/account.financial.html.report.line.csv',
        'data/record_updater.xml',
        'views/pdf_template.xml',
        'views/account_report_views.xml',
        'views/account_move.xml',
        'views/account_financial_report_line.xml',
        'views/search_template_view.xml',
        'views/account_activity_views.xml',
        'views/account_transfer_model_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'pre_init_hook': "pre_init_hook",
    'uninstall_hook': "uninstall_hook",
}
