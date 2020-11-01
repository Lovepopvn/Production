{
    'name': 'Account Counterparts',
    'version': '1.0.1',
    'category': 'Accounting',
    'summary': """
        Counterpart relations between Journal Items""",
    'description': """
The Problem
===========

In Odoo, a journal entry may contain multiple debit journal items and credit journal items.
However, there is no way for us to identify the countered line(s) of a line and its countered account(s) which may causes some troubles when:

* making reports that require showing up counterparts and countered accounts of a transaction
* identifying types of business transactions. For example, accroding to Vietnam Accounting Standards, revenues from both loan interests and exchange rate profit are also encoded into the account 515. It is impossible to build Cash Flow Statement while it requires to separate those revenues.

Features at a glance
====================

+----+---------+--------------------+-------+--------+-------------------------+
| ID | Account | Countered Accounts | Debit | Credit | Countered Journal Items |
+----+---------+--------------------+-------+--------+-------------------------+
|  1 | 131     | 5111, 5113         |   150 |      0 | [2], [3]                |
+----+---------+--------------------+-------+--------+-------------------------+
|  2 | 5111    | 131                |     0 |    100 | [1]                     |
+----+---------+--------------------+-------+--------+-------------------------+
|  3 | 5113    | 131                |       |     50 | [1]                     |
+----+---------+--------------------+-------+--------+-------------------------+

Features in Details
===================

Journal Items
-------------
The following key stored and computed fields have been added into the Journal Item model (account.move.line):

* **Countered Journal Items**: the journal items that are counterparts of the current journal item.
* **Countered Accounts**: the accounts that are counterparts of the account of the current item.
* **Countered Amount**: The matched amount that has been set as countered amount for this journal item.
* **Countered Status**: A technical field to indicate that the journal item has either countered fully or partially or not-yet-countered.

Journal Entries
---------------
The following key stored and computed fields has been added into the Journal Entry model (account.move):

* **Countered Status**: A technical field to indicate that the journal entry has either countered fully or partially or not-yet-countered.

Wizards
-------
* **Counterparts Generator** is a wizard to allow accounting manager to either generate missing counterparts for account journal items or regenerate counterparts for all the existing items. It also allow you to limit the number of entries during generation by select one or more journals

Journal Item Counterparts
-------------------------
A new technical model named 'Journal Item Counterpart' (account.move.line.ctp) is created to map a credit journal item with a debit journal item which has the following key fields:

* **dr_aml_id**: The debit journal item (also known as 'account move line')
* **cr_aml_id**: The credit journal item
* **countered_amt**: the amount that match the counterpart operation of the two journal items above mention

When a counterpart operation is carried out, a new record of the model Journal Item Counterpart will
be created to map a credit journal item with a debit journal item to indicate that the later journal item is a counterpart with a countered amount.

Some Use Cases for Proof of Concepts
------------------------------------
* Entry with One single debit item and One single credit item
    * Entry:
        * [1] Debit 131 (Customer Receivable): $100
        * [2] Credit 511 (Sales Revenue): $100
    * Counterpart Mapping:
        * Debit Line: [1]
        * Credit Line: [2]
        * Countered Amount: $100
    * List view demostration:
        +----+---------+--------------------+-------+--------+------------------------+
        | ID | Account | Countered Accounts | Debit | Credit | Countered Journal Items|
        +----+---------+--------------------+-------+--------+------------------------+
        |  1 | 131     | 511                |   100 |      0 | [2]                    |
        +----+---------+--------------------+-------+--------+------------------------+
        |  2 | 511     | 131                |     0 |    100 | [1]                    |
        +----+---------+--------------------+-------+--------+------------------------+

* Entry with One single debit item and Multiple credit items
    * Entry:
        * [1] Debit 131 (Customer Receivable): $150
        * [2] Credit 5111 (Goods Sales Revenue): $100
        * [3] Credit 5113 (Service Sales Revenue): $50
    * Counterpart Mapping:
        * 1st Counterpart:
            * Debit Line: [1]
            * Credit Line: [2]
            * Countered Amount: $100
        * 2nd Counterpart:
            * Debit Line: [1]
            * Credit Line: [3]
            * Countered Amount: $50
    * List view demonstration
        +----+---------+--------------------+-------+--------+-------------------------+
        | ID | Account | Countered Accounts | Debit | Credit | Countered Journal Items |
        +----+---------+--------------------+-------+--------+-------------------------+
        |  1 | 131     | 5111, 5113         |   150 |      0 | [2], [3]                |
        +----+---------+--------------------+-------+--------+-------------------------+
        |  2 | 5111    | 131                |     0 |    100 | [1]                     |
        +----+---------+--------------------+-------+--------+-------------------------+
        |  3 | 5113    | 131                |       |     50 | [1]                     |
        +----+---------+--------------------+-------+--------+-------------------------+

* Entry with Multipe debit items and Multiple credit items
    * Entry:
        * [1] Debit 1311 (Customer Receivable): $120
        * [2] Debit 1312 (Customer Receivable): $30
        * [3] Credit 5111 (Goods Sales Revenue): $100
        * [4] Credit 5113 (Service Sales Revenue): $50
    * Counterpart Mapping:
        * 1st Counterpart:
            * Debit Line: [2]
            * Credit Line: [3]
            * Countered Amount: $20
        * 2nd Counterpart:
            * Debit Line: [2]
            * Credit Line: [4]
            * Countered Amount: $10
        * 3rd Counterpart:
            * Debit Line: [1]
            * Credit Line: [3]
            * Countered Amount: $80
        * 4th Counterpart:
            * Debit Line: [1]
            * Credit Line: [4]
            * Countered Amount: $40
    * List view demonstration
        +----+---------+--------------------+-------+--------+-------------------------+
        | ID | Account | Countered Accounts | Debit | Credit | Countered Journal Items |
        +----+---------+--------------------+-------+--------+-------------------------+
        |  1 | 1311    | 5111, 5113         |   120 |      0 | [3], [4]                |
        +----+---------+--------------------+-------+--------+-------------------------+
        |  2 | 1312    | 5113               |    30 |      0 | [4]                     |
        +----+---------+--------------------+-------+--------+-------------------------+
        |  3 | 5111    | 1311               |     0 |    100 | [1]                     |
        +----+---------+--------------------+-------+--------+-------------------------+
        |  4 | 5113    | 1311, 1312         |     0 |     50 | [1], [2]                |
        +----+---------+--------------------+-------+--------+-------------------------+

Editions Supported
==================
1. Community Edition
2. Enterprise Edition

""",
    'author' : 'T.V.T Marine Automation (aka TVTMA)',
    'website': 'https://ma.tvtmarine.com',
    'live_test_url': 'https://v12demo-int.erponline.vn',
    'support': 'support@ma.tvtmarine.com',
    'depends': [
        'account',
    ],
    'data': [
        'data/scheduler_data.xml',
        'security/ir.model.access.csv',
        'views/account_move_line_ctp_views.xml',
        'views/account_move_line_view.xml',
        'views/account_move_view.xml',
        'wizard/wizard_account_counterpart_generator_views.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': True,
    'price': 189.9,
    'currency': 'EUR',
    'license': 'OPL-1',
}
