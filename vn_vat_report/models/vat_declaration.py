from odoo import fields, models


class VatDeclaration(models.Model):
    _name = 'vat.declaration'
    _description = 'VAT Declaration'

    name = fields.Char()
