from odoo import api, fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    @api.model
    def get_department_data_v2(self):
        final_total = 0
        Root_data = {
            "name": str(self.env.company.name) if self.env.company else "Your Company",
        }
        list_child = []
        top_department = self.env['hr.department'].sudo().search([('parent_id', '=', False)])
        department_data = {}
        if top_department:
            for department in top_department:
                children = self.get_child_department(department)
                total = 0
                if len(children) > 0:
                    for element in children:
                        total += self.count_children(element, 0)
                final_total += total
                department_data = {
                    "name": str(department.name) + "(" + str(total) + ")",
                    "children": children,
                    "title": str(department.manager_id.name) if department.manager_id else "",
                }
                list_child.append(department_data)
        Root_data["children"] = list_child
        for data in list_child:
            final_total += self.count_children(data, 0)
        Root_data["title"] = "(" + str(final_total) + ")"
        return Root_data

    def get_child_department(self, parent_department):
        child_departmnet_data = []
        children_department_ids = self.env['hr.department'].sudo().search([('parent_id', '=', parent_department.id)])
        if not children_department_ids:
            return child_departmnet_data
        else:
            for department in children_department_ids:
                children = self.get_child_department(department)
                tmp = 0
                if len(children) > 0:
                    for element in children:
                        tmp += self.count_children(element, 0)
                child_departmnet_data.append({
                    "name": str(department.name) + "(" + str(tmp) + ")",
                    "children": children,
                    "title": str(department.manager_id.name) if department.manager_id else "",

                })
        return child_departmnet_data

    def count_children(self, data, count):
        if len(data['children']) == 0:
            return count + 1
        else:
            for element in data['children']:
                return self.count_children(element, count + 1)
