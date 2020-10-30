{
    'name': 'Vietnam - Accounting VAT Report',
    'version': '13.0.1.0.0',
    'summary': 'Additional feature VAT report for vietnamese accounting standard',
    'description': """
- Sales VAT Report
- Purchase VAT Report
    """,
    'category': 'Accounting',
    'author': 'Portcities Ltd',
    'website': 'https://portcities.net',
    'depends': [
        'account_reports',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/vat_declaration_data.xml',
        'data/vat_in_configuration_data.xml',
        'data/account_account_tag_data.xml',
        'data/account_financial_html_report_data.xml',
        # 'data/account.financial.html.report.line.csv',
        'data/account_financial_html_report_line_vat_declaration.xml',
        'views/assets.xml',
        'views/vat_in_configuration_views.xml',
        'views/account_vat_out_views.xml',
        'views/account_vat_in_views.xml',
        'views/account_move_views.xml',
        'views/vn_vat_report_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
