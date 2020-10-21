# -*- coding: utf-8 -*-
'''Manufacturing Order'''
from odoo import fields, models, api


class MrpProduction(models.Model):
    '''inherit mrp.production'''
    _inherit = 'mrp.production'

    average_printing_cost_when_done = fields.Float(compute='_compute_print_cost', store=True)

    @api.depends('date_finished')
    def _compute_print_cost(self):
        # state is a computed field on MO and didn't trigger @api.depends or save through write()
        # alternatively could override _compute_state(self), but this seems to be a cleaner solution.
        for record in self:
            printing_cost = 0.0
            if record.state == 'done' and not record.average_printing_cost_when_done and record.company_id and record.company_id.factory_constants_id:
                printing_cost = record.company_id.factory_constants_id.average_printing_cost
            record.average_printing_cost_when_done = printing_cost

    # average_printing_cost_when_done = fields.Float()

    # def write(self, vals):
    #     if self.state == 'done' and not self.average_printing_cost_when_done and 'average_printing_cost_when_done' not in vals and self.company_id and self.company_id.factory_constants_id:
    #         average_printing_cost = self.company_id.factory_constants_id.average_printing_cost
    #         vals.update({'average_printing_cost_when_done': average_printing_cost})
    #     super().write(vals)
