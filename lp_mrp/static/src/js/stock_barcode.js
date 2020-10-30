odoo.define('stock_barcode.MainMenu1', function(require) {
    "use strict";

    var AbstractAction = require('stock_barcode.MainMenu').MainMenu;
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var Session = require('web.session');

    var _t = core._t;

    core.action_registry.map.stock_barcode_main_menu.include({

        events: _.defaults({
            "click .button_productlot": function() {
                this.do_action('lp_mrp.action_product_lot_shipped');
            },
        }, AbstractAction.prototype.events),

    });

});