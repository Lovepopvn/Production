from odoo.addons.stock_barcode.controllers.main import StockBarcodeController
from odoo import http, _
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)

class StockBarcodeController(StockBarcodeController):
    
    def try_open_manufacturing_order(self, barcode):
        """ If barcode represents a manufacturing_order picking, open it
        """
        corresponding_manufacturing_order = request.env['mrp.production'].search([
            ('name', '=', barcode),
        ], limit=1)
        _logger.info("Open Manufacturing Order %s" % corresponding_manufacturing_order)
        if corresponding_manufacturing_order:
            return self.get_action_manufacturing_order(corresponding_manufacturing_order.id)
        return False

    @http.route('/stock_barcode/scan_from_main_menu', type='json', auth='user')
    def main_menu(self, barcode, **kw):
        """ Receive a barcode scanned from the main menu and return the appropriate
            action (open an existing / new manufacturing_order) or warning.
        """
        _logger.info("Main Manufacturing Order %s" % barcode)
        ret_open_manufacturing_order = self.try_open_manufacturing_order(barcode)
        if ret_open_manufacturing_order:
            return ret_open_manufacturing_order
        return super(StockBarcodeController, self).main_menu(barcode, **kw)
    
    def get_action_manufacturing_order(self, manufacturing_order_id):
        """
        return the action to display the manufacturing_order picking
        """
        view_id = request.env.ref('mrp.mrp_production_form_view').id
        return {
            'action': {
                'name': _('Open manufacturing_order form'),
                'res_model': 'mrp.production',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': view_id,
                'views': [(view_id, 'form')],
                'type': 'ir.actions.act_window',
                'res_id': manufacturing_order_id,
            }
        }
