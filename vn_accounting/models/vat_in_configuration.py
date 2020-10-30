from odoo import api, fields, models


class VatInConfiguration(models.Model):
    _name = 'vat.in.configuration'

    name = fields.Char('VAT category name')
    allocated_to_vat_declaration = fields.Many2one('vat.declaration')
    default_vat_in = fields.Boolean('Default')

    @api.model
    def create(self,vals):
        if vals.get('default_vat_in'):
            vats_in = self.search([('default_vat_in','=',True)])
            vats_in.write({'default_vat_in': False})
        return super(VatInConfiguration, self).create(vals)
 
    
    def write(self,vals):
        super(VatInConfiguration, self).write(vals)
        for rec in self:
            if rec.default_vat_in:
                vats_in = rec.search([('id','!=',rec.id),('default_vat_in','=',True)])
                vats_in.update({'default_vat_in': False})
