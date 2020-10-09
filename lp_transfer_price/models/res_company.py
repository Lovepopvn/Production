# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    transfer_price_update_scheduler_id = fields.Many2one('ir.cron', \
        'Scheduler for Transfer Price Update', readonly=True, \
        related="company_id.transfer_price_update_scheduler_id")
    transfer_price_update_pricelist_id = fields.Many2one('product.pricelist', \
        'Pricelist For Transfer Price Update', readonly=False,\
        related='company_id.transfer_price_update_pricelist_id')


class ResCompany(models.Model):
    """ Inherit res company """
    _inherit = 'res.company'

    transfer_price_update_scheduler_id = fields.Many2one('ir.cron', \
        'Scheduler for Transfer Price Update')
    transfer_price_update_pricelist_id = fields.Many2one('product.pricelist', \
        'Pricelist For Transfer Price Update')

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        if 'transfer_price_update_pricelist_id' in vals:
            pricelist_id = vals.get('transfer_price_update_pricelist_id')
            if not pricelist_id:
                schedulers = self.mapped('transfer_price_update_scheduler_id')
                if schedulers:
                    schedulers.write({'active': False})
            else:
                self = self.sudo()
                now = datetime.now()
                # ICT timezone = UTC+07 → subtracting 7 hours from UTC midnight
                call_time = now.replace(hour=0, minute=0, second=0, microsecond=0) \
                    + timedelta(days=1) - timedelta(hours=7)
                for company in self:
                    cron_values = {
                        'name': "[%s] Transfer Price Update" % company.name,
                        'model_id': self.env.ref('product.model_product_pricelist').id,
                        'state': 'code',
                        'active': True,
                        'doall': True,
                        'user_id': self.env.ref('base.user_admin').id,
                        'interval_number': 1,
                        'interval_type': 'days',
                        'numbercall': -1,
                        'nextcall': call_time,
                        'code': "model.transfer_price_update(%d)" % company.id,
                    }
                    if company.transfer_price_update_scheduler_id:
                        company.transfer_price_update_scheduler_id.write(cron_values)
                    else:
                        new_cron = self.env['ir.cron'].create(cron_values)
                        company.write({'transfer_price_update_scheduler_id': new_cron.id})
        return res
