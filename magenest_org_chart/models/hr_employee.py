from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def get_employee_data_v2(self):
        final_total = 0
        Root_data = {
            "name": str(self.env.company.name) if self.env.company else "Your Company",
            'className': 'middle-level',
        }
        list_child = []
        top_employee = self.env['hr.employee'].sudo().search([('parent_id', '=', False)])
        employee_data = {}
        if top_employee:
            for employee in top_employee:
                if employee.user_id:
                    children = self.get_child_employee(employee)
                    total = 0
                    if len(children) > 0:
                        for element in children:
                            total += self.count_children(element, 0)
                    final_total += total
                    employee_data = {
                        "name": str(employee.name) + "(" + str(total) + ")",
                        "title": str(employee.department_id.name) if employee.department_id else "",
                        "children": children
                    }
                    list_child.append(employee_data)
        Root_data["children"] = list_child
        for data in list_child:
            final_total += self.count_children(data, 0)
        Root_data["title"] = "(" + str(final_total) + ")"
        return Root_data

    def get_child_employee(self, parent_employee):
        child_employee_data = []
        children_employee_ids = self.env['hr.employee'].sudo().search([('parent_id', '=', parent_employee.id)])
        if not children_employee_ids:
            return child_employee_data
        else:
            for employee in children_employee_ids:
                children = self.get_child_employee(employee)
                tmp = 0
                if len(children) > 0:
                    for element in children:
                        tmp += self.count_children(element, 0)
                child_employee_data.append({
                    "name": str(employee.name) + "(" + str(tmp) + ")",
                    "title": str(employee.department_id.name) if employee.department_id else "",
                    "children": self.get_child_employee(employee)
                })
        return child_employee_data

    def count_children(self, data, count):
        if len(data['children']) == 0:
            return count + 1
        else:
            for element in data['children']:
                return self.count_children(element, count + 1)
