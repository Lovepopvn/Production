
odoo.define('vn_accounting.invoice_number', function (require) {
    'use strict';
    
    var core = require('web.core');
    var Context = require('web.Context');
    var AbstractAction = require('web.AbstractAction');
    var ControlPanelMixin = require('web.ControlPanelMixin');
    var Dialog = require('web.Dialog');
    var crash_manager = require('web.crash_manager');
    var datepicker = require('web.datepicker');
    var session = require('web.session');
    var field_utils = require('web.field_utils');
    var RelationalFields = require('web.relational_fields');
    var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
    var Widget = require('web.Widget');
    
    var QWeb = core.qweb;
    var _t = core._t;

    var account_report = require('account_reports.account_report')
    account_report.include({
        render_searchview_buttons: function(){
            this._super();
            var self = this;
            this.$searchview_buttons.find('.js_account_report_inv_number_filter').click(function (event) {
                self.report_options[$(this).data('filter')] = $('#invoice_number').val();
                self.reload();
            });

        }
    })


})