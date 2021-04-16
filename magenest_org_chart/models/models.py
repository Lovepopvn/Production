# -*- coding: utf-8 -*-
from odoo import models, fields, api


class OrgChartDepartment(models.Model):
    _name = 'org.chart.department'

    name = fields.Char("Org Chart Department")

    @api.model
    def get_department_data(self):
        departments = []
        # get all department and level
        level = 0
        roots = self.env['hr.department'].search([('parent_id', '=', False)])
        for root in roots:
            children_data = self.get_department_child(root, level + 1)
            if len(children_data) > 0:
                for e in children_data:
                    departments.append(e)
        # sort department by level
        data = []
        departments = sorted(departments, key=lambda k: k['level'])
        group_child = []
        group_parent = []
        for department in departments:
            department_data = department['department']
            department_name = department_data.name
            if len(department_name) > 14:
                department_name = self.acronym_name_string(department_name, type=True)
            department_manager_image = False
            department_manager_name = 'No manager'
            if department_data.manager_id.id:
                department_manager_name = department_data.manager_id.name
                # if len(department_manager_name) > 20:
                department_manager_name = self.acronym_name_string(department_manager_name, type=True)
                department_manager_image = self.env['ir.config_parameter'].sudo().get_param(
                    'web.base.url') + '/web/image/hr.employee/' + str(
                    department_data.manager_id.id) + '/image/170x170',
            data.append({
                'id': department_data.id,
                'pid': department_data.parent_id.id,
                'name': department_name,
                'manager_name': department_manager_name,
                'img': department_manager_image,
                'level': department['level'],
                'num_employee': len(self.env['hr.employee'].search([('department_id', '=', department_data.id)]).ids)
            })
            if department_data.id:
                group_child.append(department_data.id)
            if department_data.parent_id.id and department_data.parent_id.id not in group_parent:
                group_parent.append(department_data.parent_id.id)
        tags = []
        for element in group_parent:
            tags.append("Group" + str(element))
        group_child_delete = []
        for element in group_child:
            if element in group_parent:
                group_child_delete.append(element)
        for element in group_child_delete:
            group_child.remove(element)
        for line in data:
            if line['pid'] in group_parent and line['id'] in group_child:
                line['tags'] = ["Group" + str(line['pid'])]
                # line['tags'] = ["name_group"]
        # return data
        # print(tags)
        # print(data)
        return {
            'data': data,
            'tags': tags
        }

    def get_department_child(self, root, level):
        result = []
        departments = self.env['hr.department'].search([('parent_id', '=', root.id)])
        for department in departments:
            children_data = self.get_department_child(department, level + 1)
            if len(children_data) > 0:
                for e in children_data:
                    result.append(e)
        result.append({
            'department': root,
            'level': level
        })
        return result

    def acronym_name_string(self, string, type=None):
        full_name = string.split('(')[0]
        last_name = full_name.split().pop()
        pretreatment = '.'.join(w[0].upper() for w in full_name.split()[:-1])
        if pretreatment != '':
            aro_str = pretreatment + '.' + last_name
        else:
            aro_str = last_name
        if type is None:
            if len(aro_str.split('.')) > 3:
                new = ''
                for i in range(len(aro_str.split('.')) - 2):
                    new += (aro_str.split('.')[i] + '.')
                new = new + string.split()[
                    len(aro_str.split('.')) - 2] + '.' + \
                      string.split()[len(aro_str.split('.')) - 1]
            elif len(aro_str.split('.')) == 3:
                new = aro_str.split('.')[0] + '.' + aro_str.split('.')[1] + '.' + string.split()[
                    len(aro_str.split('.')) - 1]
            else:
                new = aro_str
            return new
        return aro_str


class OrgChartEmployee(models.Model):
    _name = 'org.chart.employee'

    name = fields.Char("Org Chart Employee")

    @api.model
    def get_employee_data(self):
        employees = []
        # get all employee and level
        level = 0
        roots = self.env['hr.employee'].search([('parent_id', '=', False)])
        for root in roots:
            children_data = self.get_employee_child(root, level + 1)
            if len(children_data) > 0:
                for e in children_data:
                    employees.append(e)
        # sort employee by level
        data = []
        group_child = []
        group_parent = []
        employees = sorted(employees, key=lambda k: k['level'])
        for employee in employees:
            employee_data = employee['employee']
            # employee_name = employee_data.name
            # if len(employee_data.name) > 18:
            employee_name = self.acronym_name_string(employee_data.name)
            # department = self.env['hr.department'].search([('manager_id', '=', employee_data.id)])
            # if not department:
            #     department = employee_data.job_id.name
            # else:
            #     department = department.name
            # if department:
            #     if len(department) > 14:
            #         department = self.acronym_name_string(department, type=True)
            get_employee = self.env['hr.employee'].search([('id', '=', employee_data.id)])
            if get_employee.department_id:
                department_name = get_employee.department_id.name
            else:
                department_name = ""
            employee_image = self.env['ir.config_parameter'].sudo().get_param(
                'web.base.url') + '/web/image/hr.employee/' + str(
                employee_data.id) + '/image/170x170',
            data.append({
                'id': employee_data.id,
                'pid': employee_data.parent_id.id,
                'name': employee_name,
                'department_name': department_name,
                'img': employee_image,
                'level': employee['level'],
            })
            if employee_data.id:
                group_child.append(employee_data.id)
            if employee_data.parent_id.id and employee_data.parent_id.id not in group_parent:
                group_parent.append(employee_data.parent_id.id)
        tags = []
        for element in group_parent:
            tags.append("Group" + str(element))
        group_child_delete = []
        for element in group_child:
            if element in group_parent:
                group_child_delete.append(element)
        for element in group_child_delete:
            group_child.remove(element)
        for line in data:
            if line['pid'] in group_parent and line['id'] in group_child:
                line['tags'] = ["Group" + str(line['pid'])]
        return {
            'data': data,
            'tags': tags
        }

    def get_employee_child(self, root, level):
        result = []
        employees = self.env['hr.employee'].search([('parent_id', '=', root.id)])
        for employee in employees:
            children_data = self.get_employee_child(employee, level + 1)
            if len(children_data) > 0:
                for e in children_data:
                    result.append(e)
        result.append({
            'employee': root,
            'level': level
        })
        return result

    def acronym_name_string(self, string, type=None):
        full_name = string.split('(')[0]
        last_name = full_name.split().pop()
        pretreatment = '.'.join(w[0].upper() for w in full_name.split()[:-1])
        if pretreatment != '':
            aro_str = pretreatment + '.' + last_name
        else:
            aro_str = last_name
        if type is None:
            if len(aro_str.split('.')) > 3:
                new = ''
                for i in range(len(aro_str.split('.')) - 2):
                    new += (aro_str.split('.')[i] + '.')
                new = new + string.split()[
                    len(aro_str.split('.')) - 2] + '.' + \
                      string.split()[len(aro_str.split('.')) - 1]
            elif len(aro_str.split('.')) == 3:
                new = aro_str.split('.')[0] + '.' + aro_str.split('.')[1] + '.' + string.split()[
                    len(aro_str.split('.')) - 1]
            else:
                new = aro_str
            return new
        return aro_str
