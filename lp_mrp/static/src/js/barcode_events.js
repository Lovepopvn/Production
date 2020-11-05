odoo.define('lp_mrp.ListController', function(require) {
    "use strict";
    var rpc = require('web.rpc');
    var core = require('web.core');
    var ListController = require('web.ListController')
    var concurrency = require('web.concurrency');
    var Dialog = require('web.Dialog');

    var _t = core._t;

    ListController.include({
        custom_events: _.extend({}, ListController.prototype.custom_events, {
            activeBarcode: '_barcodeActivated',
        }),

        /**
         * add default barcode commands for from view
         *
         * @override
         */
        init: function(parent, model, renderer, params) {
            this._super.apply(this, arguments);
            this.activeBarcode = {
                list_view: {
                    commands: {
                        'O-CMD.EDIT': this._barcodeEdit.bind(this),
                        'O-CMD.DISCARD': this._barcodeDiscard.bind(this),
                        'O-CMD.SAVE': this._barcodeSave.bind(this),
                    },
                },
            };

            this.barcodeMutex = new concurrency.Mutex();
            this._barcodeStartListening();
        },

        /**
         * @override
         */
        destroy: function() {
            this._barcodeStopListening();
            this._super();
        },

        _barcodeEdit: function() {
            return this._setMode('edit');
        },

        _barcodeDiscard: function() {
            return this.discardChanges();
        },

        _barcodeSave: function() {
            return this.saveRecord();
        },

        /**
         * @private
         */
        _barcodeStartListening: function() {
            core.bus.on('barcode_scanned', this, this._barcodeScanned);
        },
        /**
         * @private
         */
        _barcodeStopListening: function() {
            core.bus.off('barcode_scanned', this, this._barcodeScanned);
        },

        _barcodeScanned: function(barcode, target) {
            var self = this;
            var model = self.modelName;
            if (model == 'product.lot') {
                rpc.query({
                    model: 'product.lot',
                    method: 'get_barcode_info',
                    args: [barcode],
                }).then(function(barcode_info) {
                    console.log("#############")
                    console.log(barcode_info)
                    if (barcode_info == false) {
                        Dialog.alert(this, _t("Data not Found! Please check your barcode code !"), { title: _t("Warning") });
                    } else {
                        console.log("RELOADDDDDDD")
                        self.update({}, {reload: true});
                    }
                });
            }
            return true
        },

        _barcodeActivated: function(event) {
            event.stopPropagation();
            var name = event.data.name;
            this.activeBarcode[name] = {
                name: name,
                handle: this.handle,
                target: event.target,
                widget: event.target.attrs && event.target.attrs.widget,
                setQuantityWithKeypress: !!event.data.setQuantityWithKeypress,
                fieldName: event.data.fieldName,
                notifyChange: (event.data.notifyChange !== undefined) ? event.data.notifyChange : true,
                quantity: event.data.quantity,
                commands: event.data.commands || {},
                candidate: this.activeBarcode[name] && this.activeBarcode[name].handle === this.handle ?
                    this.activeBarcode[name].candidate : null,
            };

            // we want to disable autofocus when activating the barcode to avoid
            // putting the scanned value in the focused field
            this.disableAutofocus = true;
        },
    })
})