var my_department_data = [];
odoo.define("org_chart_organization.org_chart_department", function (require) {
    "use strict";
    var tags = {};
    var core = require('web.core');
    var ajax = require('web.ajax');
    var AbstractAction = require('web.AbstractAction');
    var QWeb = core.qweb;
    var OrgChartDepartment = AbstractAction.extend({
        init: function (parent, context) {
            this._super(parent, context);
            var self = this;
            if (context.tag == 'org_chart_department') {
                self._rpc({
                    model: 'org.chart.department',
                    method: 'get_department_data',
                }, []).then(function (result) {
                    my_department_data = [];
                    for (var i = 0; i < result['data'].length; i++) {
                        if (result['data'][i]['pid'] === false) {
                            result['data'][i]['pid'] = null;
                        }
                        my_department_data.push(result['data'][i])
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
            var self = this;
            var org_chart = QWeb.render('org_chart_organization.get_org_chart_template', {
                widget: self,
            });
            $(".o_control_panel").addClass("o_hidden");
            $(self.$el[0]).html(org_chart)
            return true;
        },
        reload: function () {
            window.location.href = this.href;
        }
    });

    core.action_registry.add('org_chart_department', OrgChartDepartment);
    return {
        OrgChartDepartment: OrgChartDepartment
    };

});
