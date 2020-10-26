odoo.define('vn_accounting.account_report', function (require) {
    'use strict';

    var AccountReport = require('account_reports.account_report');

    AccountReport.include({
        render_searchview_buttons: function() {
            var self = this
            this.$searchview_buttons.find('.js_account_report_vat_customer_filter').click(function (event){
                var vat_number = $(this).parent().find('input[id="vat_number"]')[0].value;
                self.report_options['vat_number'] = vat_number;
                self.reload();
            });
            this._super.apply(this, arguments);
        }
    })
})
