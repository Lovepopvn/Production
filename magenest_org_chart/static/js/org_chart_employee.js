var employee_data = [];
var tags = {};
odoo.define("org_chart_organization.org_chart_employee", function (require) {
    "use strict";

    var core = require('web.core');
    var session = require('web.session');
    var ajax = require('web.ajax');
    var Widget = require('web.Widget');
    var ControlPanelMixin = require('web.ControlPanelMixin');
    var QWeb = core.qweb;
    var _t = core._t;
    var _lt = core._lt;

    var OrgChartEmployee = Widget.extend(ControlPanelMixin, {
        init: function (parent, context) {
            this._super(parent, context);
            var self = this;
            if (context.tag == 'org_chart_organization.org_chart_employee') {
                self._rpc({
                    model: 'org.chart.employee',
                    method: 'get_employee_data',
                }, []).then(function (result) {
                    employee_data = [];
                    for (var i = 0; i < result['data'].length; i++) {
                        if (result['data'][i]['pid'] === false) {
                            result['data'][i]['pid'] = null;
                        }
                        employee_data.push(result['data'][i])
                    }
                    for (var i = 0; i < result['tags'].length; i++) {
                        var name_group = String(result['tags'][i]);
                        tags[name_group] = {
                                group: true,
                                groupName: "Group",
                                groupState: OrgChart.EXPAND,
                                template: "group_grey"
                            }
                    }
                    console.log(employee_data)
                }).done(function () {
                    self.render();
                    self.href = window.location.href;
                });
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
            var super_render = this._super;
            var self = this;
            // var org_chart = QWeb.render('org_chart_organization.employee_org_chart_template', {
            //     widget: self,
            // });
             var org_chart = QWeb.render('org_chart_organization.get_employee_org_chart_template', {
                widget: self,
            });


            $(".o_control_panel").addClass("o_hidden");
            $(org_chart).prependTo(self.$el);
            return org_chart;
        },
        reload: function () {
            window.location.href = this.href;
        },
        canBeRemoved: function () {
            return $.when();
        },
        on_attach_callback: function () {},
        on_detach_callback: function () {},
    });

    core.action_registry.add('org_chart_organization.org_chart_employee', OrgChartEmployee);

    return OrgChartEmployee;

});
