from datetime import timedelta
from odoo import models, fields


class AccountTransferModel(models.Model):
    _inherit = 'account.transfer.model'

    is_period_end = fields.Boolean(string='Period End Posting')

    def _create_or_update_move_for_period(self, start_date, end_date):
        """ Extend _create_or_update_move_for_period() """
        self.ensure_one()
        if self.is_period_end and end_date < self.date_stop:
            end_date -= timedelta(days=1)
        return super()._create_or_update_move_for_period(start_date, end_date)
