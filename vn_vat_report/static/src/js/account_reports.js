odoo.define('vn_vat_report.account_report', function (require) {
    'use strict';

    var AccountReport = require('account_reports.account_report');

    AccountReport.include({
        render_searchview_buttons: function(){
            this._super();
            var self = this;
            this.$searchview_buttons.find('.js_account_report_inv_number_filter').click(function (event) {
                self.report_options[$(this).data('filter')] = $('#invoice_number').val();
                self.reload();
            });

            this.$searchview_buttons.find('.js_account_report_tax_filter').click(function(e) {
                self.report_options[$(this).data('filter')] = $('#tax_name').val();
                self.reload();
            });
        }
    })
})
