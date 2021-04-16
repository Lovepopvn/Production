var department_data = {}
odoo.define("org_chart_organization.org_chart_department_v2", function (require) {
    "use strict";
    var tags = {};
    var core = require('web.core');
    var ajax = require('web.ajax');
    var AbstractAction = require('web.AbstractAction');
    var QWeb = core.qweb;
    var OrgChartDepartment = AbstractAction.extend({
        template: "org_chart_organization.get_org_chart_department_template",
        jsLibs: [
            '/org_chart_organization/static/js/jquery.orgchart.js'
        ],
        init: function (parent, context) {
            this._super(parent, context);
            var self = this;
            if (context.tag == 'org_chart_department_v2') {
                self._rpc({
                    model: 'hr.department',
                    method: 'get_department_data_v2',
                }).then(function (result) {
                    department_data = result
                    self.render();
                });
                this.href = window.location.href;
            }
        },

        willStart: function () {
            return $.when(ajax.loadLibs(this), this._super());
        },
        start: function () {
            var self = this;
            return this._super();
        },
        render: function () {
            this._super;
            var self = this;
            var org_chart = QWeb.render('org_chart_organization.get_org_chart_department_template', {});
            // console.log(this)
            $(".o_control_panel").addClass("o_hidden");
            return org_chart;
        },
        reload: function () {
            window.location.href = this.href;
        }
    });

    core.action_registry.add('org_chart_department_v2', OrgChartDepartment);
    return {
        OrgChartDepartment: OrgChartDepartment
    };

});
