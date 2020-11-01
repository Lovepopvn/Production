
{
    'name': 'VAT Declaration Report',
    'version': '12.0.1.0.0',
    'summary': 'Generate VAT Declaration report in PDF and XLSX',
    'description': """
    v.1.0 (Ahmad) \n
        Generate VAT Declaration report in PDF and XLSX
    v.2.0 (Ahmad) \n
        Generate VAT Allocation report in PDF and XLSX
    """,
    'category': 'Accounting',
    'author': 'Portcities Ltd',
    'website': 'https://portcities.net',
    'depends': [
        'vn_vat_report',
    ],
    'data': [
        # 'security/ir.model.access.csv',
        'views/account_tax.xml',
        'views/account_menu.xml',
        
        'wizard/vat_declaration_views.xml',
        'wizard/vat_allocation_views.xml',
        'reports/vat_declaration_report.xml',
        'reports/vat_allocation_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}
