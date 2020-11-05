from odoo import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    tag_ids = fields.Many2many('account.account.tag', 'tax_tags_rel', 'tax_id', 'tag_id')
