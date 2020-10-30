from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountActivity(models.Model):
    _name = 'account.activity'
    _description = "Master of Account Activities"

    code = fields.Char(string=_("Code"))
    name = fields.Char(string=_("Name"), required=True, translate=True)

    @api.model
    def create(self, vals_list):
        new_code = '001'
        last_code = self.search([], order='code desc', limit=1)
        if last_code:
            code = int(last_code.code) + 1
            if code < 10:
                new_code = '00%d' % (code,)
            elif code < 100:
                new_code = '0%d' % (code,)
            else:
                new_code = str(code)

        vals_list['code'] = new_code
        return super(AccountActivity, self).create(vals_list)


class AccountActivityOperation(models.Model):
    _name = 'account.activity.operation'
    _description = "Account operation activities"

    name = fields.Char(string=_("Code"), required=True)
    activity_id = fields.Many2one('account.activity', string="Account Activity", required=True)
    activity_code = fields.Char(string="Activity Code", related='activity_id.code', store=True)
    account_debit_ids = fields.Many2many('account.account', 'account_activity_operation_debit_rel', 'account_id',
                                         'account_operation_activity_debit_id', string=_("Debit"), required=False)
    account_credit_ids = fields.Many2many('account.account', 'account_activity_operation_credit_rel', 'account_id',
                                          'account_operation_activity_credit_id', string=_("Credit"), required=False)

    

    
    def name_get(self):
        res = []
        short = self._context.get('short_name')
        for record in self:
            if short:
                name = '%s - %s' % (record.name, "%s..." % (record.activity_id.name[0:200] if len(record.activity_id.name)>=200 else record.activity_id.name, ) )
            else:
                name = '%s - %s' % (record.name, record.activity_id.name )
            res.append((record.id, name))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=80):
        if not args:
            args = []
        if name:
            args += ['|', ('name', operator, name), ('activity_id.name', operator, name)]
        record = self.search(args, limit=limit)
        return record.name_get()

    @api.constrains('account_debit_ids', 'account_credit_ids')
    def _check_validation(self):
        """ Check validation same debit and credit. """
        for operation in self:
            if not operation.account_debit_ids and not operation.account_credit_ids:
                raise ValidationError(_("User must input debit account or credit account or both"))

            debit_ids = operation.account_debit_ids.mapped('id')
            credit_ids = operation.account_credit_ids.mapped('id')
            intersection = set(debit_ids) & set(credit_ids)
            if intersection:
                raise ValidationError(_("Debit and Credit must not contain the same value."))
