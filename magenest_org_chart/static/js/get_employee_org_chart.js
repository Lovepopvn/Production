odoo.define(function (require) {
    "use strict";
    var chart = new OrgChart(document.getElementById("employees"), {
        template: "isla",
        nodeMouseClick: OrgChart.action.none,
        menu: {
            pdf: {text: "Export PDF"},
            png: {text: "Export PNG"},
            svg: {text: "Export SVG"},
            csv: {text: "Export CSV"}
        },
        lazyLoading: true,
        scaleMax: 2,
        nodeBinding: {
            field_0: "name",
            field_1: "department_name",
            img_0: "img"
        },
        searchFields: ["name", "department_name"],
        zoom: {
            speed: 150,
            smooth: 2
        },
        tags: tags,
        nodes: employee_data,
        scaleInitial: 0.3,
    });
});