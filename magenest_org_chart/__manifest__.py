# -*- coding: utf-8 -*-
{
    'name': "Organization Chart Department",
    'summary': """Dynamic display of your Department Organization""",
    'description': """Dynamic display of your Department Organization""",
    'author': "Magenest",
    'website': "http://magenest.com/",
    'category': 'Human Resources',
    'version': '2.0',
    'depends': ['base', 'hr', 'web', 'website'],
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/chart_views.xml',
        'views/chart_views_v2.xml',
    ],
    'qweb': [
        # "static/src/xml/org_chart_department.xml",
        # "static/src/xml/org_chart_employee.xml",
        "static/src/xml/org_chart_department_v2.xml",
        "static/src/xml/org_chart_employee_v2.xml",
    ],
    'images': ['static/description/thumbnail.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
}
