# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Department(models.Model):
    _name = "hr.department"
    _description = "Department"
    _inherit = ['mail.thread']
    _order = "name"
    _rec_name = 'complete_name'

    name = fields.Char('Department Name', required=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', recursive=True, store=True)
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    parent_id = fields.Many2one('hr.department', string='Parent Department', index=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    child_ids = fields.One2many('hr.department', 'parent_id', string='Child Departments')
    manager_id = fields.Many2one('hr.employee', string='Manager', tracking=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    member_ids = fields.One2many('hr.employee', 'department_id', string='Members', readonly=True)
    total_employee = fields.Integer(compute='_compute_total_employee', string='Total Employee')
    jobs_ids = fields.One2many('hr.job', 'department_id', string='Jobs')
    note = fields.Text('Note')
    color = fields.Integer('Color Index')

    def name_get(self):
        if not self.env.context.get('hierarchical_naming', True):
            return [(record.id, record.name) for record in self]
        return super(Department, self).name_get()

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for department in self:
            if department.parent_id:
                department.complete_name = '%s / %s' % (department.parent_id.complete_name, department.name)
            else:
                department.complete_name = department.name

    def _compute_total_employee(self):
        emp_data = self.env['hr.employee'].read_group([('department_id', 'in', self.ids)], ['department_id'], ['department_id'])
        result = dict((data['department_id'][0], data['department_id_count']) for data in emp_data)
        for department in self:
            department.total_employee = result.get(department.id, 0)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive departments.'))

    @api.model_create_multi
    def create(self, vals_list):
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        departments = super(Department, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        for department, vals in zip(departments, vals_list):
            manager = self.env['hr.employee'].browse(vals.get("manager_id"))
            if manager.user_id:
                department.message_subscribe(partner_ids=manager.user_id.partner_id.ids)
        return departments

    def write(self, vals):
        """ If updating manager of a department, we need to update all the employees
            of department hierarchy, and subscribe the new manager.
        """
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        if 'manager_id' in vals:
            manager_id = vals.get("manager_id")
            if manager_id:
                manager = self.env['hr.employee'].browse(manager_id)
                # subscribe the manager user
                if manager.user_id:
                    self.message_subscribe(partner_ids=manager.user_id.partner_id.ids)
            # set the employees's parent to the new manager
            self._update_employee_manager(manager_id)
        return super(Department, self).write(vals)

    def _update_employee_manager(self, manager_id):
        employees = self.env['hr.employee']
        for department in self:
            employees = employees | self.env['hr.employee'].search([
                ('id', '!=', manager_id),
                ('department_id', '=', department.id),
                ('parent_id', '=', department.manager_id.id)
            ])
        employees.write({'parent_id': manager_id})

    def get_formview_action(self, access_uid=None):
        res = super().get_formview_action(access_uid=access_uid)
        if (not self.user_has_groups('hr.group_hr_user') and
           self.env.context.get('open_employees_kanban', False)):
            res.update({
                'name': self.name,
                'res_model': 'hr.employee.public',
                'view_type': 'kanban',
                'view_mode': 'kanban',
                'views': [(False, 'kanban'), (False, 'form')],
                'context': {'searchpanel_default_department_id': self.id},
                'res_id': False,
            })
        return res
