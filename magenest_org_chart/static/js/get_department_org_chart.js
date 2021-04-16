console.log(my_department_data)
var chart = new OrgChart(document.getElementById("departments"), {
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
            field_1: "manager_name",
            img_0: "img"
        },
        searchFields: ["name", "manager_name"],
        zoom: {
            speed: 150,
            smooth: 2
        },
        tags: tags,
        nodes: my_department_data,
        scaleInitial: 0.5,
    });