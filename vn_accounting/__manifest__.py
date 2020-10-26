
{
    'name': 'Vietnam - Accounting Complete (DON\'T USE THIS, USE VN_VAS_REPORT , VN_VAT_REPORT)',
    'version': '12.0.1.0.0',
    'summary': 'Additional feature for vietnamese accounting standard',
    'description': """
        not complete yet
        need: account counterparts module, need vn200 module
    """,
    'category': 'Accounting',
    'author': 'Portcities Ltd',
    'website': 'https://portcities.net',
    'contributors': [
        'Tran Chi Tien',
        'Dhimas Yudangga A',
        'Alvin Adjie P',
        'Elsa Damayanti Y',
    ],
    'depends': [
        'account',
        'account_reports',
        'l10n_vn',
        'to_account_counterpart',
        'account_type_menu',
        'account_account_english'
    ],
    'data': [
        'data/account_type.xml',
        'data/account.account.csv',
        # 'data/account_account.xml',
        'data/account_journal.xml',
        'data/account_account_tags_data.xml',
        'data/account_financial_report_vd_data.xml',
        'data/account_financial_report_bs_b01_data.xml',
        'data/account_financial_report_pnl_b02_data.xml',
        'data/account_financial_report_icf_b03_data.xml',
        'data/vat_declaration_data.xml',
        'data/account_vat_out.xml',
        'data/account.activity.csv',
        'data/account.financial.html.report.line.csv',

        'views/pdf_template.xml',

        'views/account_report_views.xml',
        'views/vat_in_configuration.xml',
        'views/account_move.xml',
        'views/js_template.xml',
        'views/account_financial_report_line.xml',
        'views/search_template_view.xml',
        'views/account_activity_views.xml',

        'data/record_updater.xml',
        'security/ir.model.access.csv',
        
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'pre_init_hook': "pre_init_hook",
    'uninstall_hook': "uninstall_hook",
}
