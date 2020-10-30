from odoo import api, fields, models, SUPERUSER_ID, _


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _get_product_purchase_description(self, product_lang):
        res = super(PurchaseOrderLine, self)._get_product_purchase_description(product_lang)
        if product_lang.fsc_group_id or product_lang.fsc_status_id:
            if product_lang.fsc_group_id and product_lang.fsc_status_id:
                res += ' - ' + product_lang.fsc_group_id.name + ' ' + product_lang.fsc_status_id.name
            elif product_lang.fsc_group_id and not product_lang.fsc_status_id:
                res += ' - ' + product_lang.fsc_group_id.name
            elif not product_lang.fsc_group_id and product_lang.fsc_status_id:
                res += ' - ' + product_lang.fsc_status_id.name
        return res
    