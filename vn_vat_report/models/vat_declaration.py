from odoo import fields, models


class VatDeclaration(models.Model):
    _name = 'vat.declaration'

    name = fields.Char()
