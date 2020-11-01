from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
	_inherit = 'account.move'
	
	debit_account_codes = fields.Char(string="Debit Codes", compute="_compute_line_account_id", store=True)
	credit_account_codes = fields.Char(string="Credit Codes", compute="_compute_line_account_id", store=True)
	activity_operation_id = fields.Many2one('account.activity.operation', string=_("Activity"))

	@api.onchange('line_ids')
	def _onchange_line_account_id(self):
		""" Set default value for activity_operation_id """
		debit_line = self.line_ids.filtered(lambda r: r.debit > 0 and r.credit <= 0)
		credit_line = self.line_ids.filtered(lambda r: r.credit > 0  and r.debit <= 0)
		account_debit_ids = debit_line.mapped('account_id')
		account_credit_ids = credit_line.mapped('account_id')
		self.activity_operation_id = self.env['account.activity.operation'].search([
			('account_debit_ids', 'in', account_debit_ids.ids),
			('account_credit_ids', 'in', account_credit_ids.ids)
		], limit=1)

	@api.model
	def search_test(self, debit_code, credit_code=None):
		found = self.search([('debit_account_ids','=',debit_code),('credit_account_ids','=','911'),('journal_id.code','=','CLOSE')])
		print(found)
		_logger.info("Found %s" % (len(found)))
	
	@api.model
	def name_search(self, name, args=None, operator='ilike', limit=100):
		res = super().name_search(name, args, operator, limit)
		# _logger.critical((">>>>>", res))
		return res

	@api.depends('line_ids.account_id')
	def _compute_line_account_id(self):
		for rec in self:
			debit_line = rec.line_ids.filtered(lambda r:r.debit>0.0 and r.credit<=0.0)
			credit_line = rec.line_ids.filtered(lambda r:r.credit>0.0 and r.debit<=0.0)
			debit_accounts = debit_line.mapped('account_id')
			credit_accounts = credit_line.mapped('account_id')
			rec.update({
				'debit_account_codes':",".join(debit_accounts.mapped('code')),
				'credit_account_codes':",".join(credit_accounts.mapped('code')),
			})


class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'

	purchased_vat_category = fields.Many2one('vat.in.configuration', string="Purchased VAT category")
	journal_type = fields.Selection([],related="move_id.journal_id.type")
	date_accounting = fields.Date()
	debit_account_codes = fields.Char(string="Debit Codes", related="move_id.debit_account_codes", readonly=True)
	credit_account_codes = fields.Char(string="Credit Codes", related="move_id.credit_account_codes", readonly=True)
	activity_operation_id = fields.Many2one('account.activity.operation', related='move_id.activity_operation_id',
											string=_("Activity"), store=True)

	ctp_account_count = fields.Integer(string="Counterpart Account Counter", compute="_compute_ctp_account_ids", store=True)

	# this field should be used only for filter purpose
	ctp_reversed_aml = fields.Char(compute="_compute_ctp_reversed_aml", search="_search_ctp_reversed_aml")

	@api.depends('ctp_aml_ids', 'ctp_aml_ids.account_id')
	def _compute_ctp_account_ids(self):
		super(AccountMoveLine, self)._compute_ctp_account_ids()
		for rec in self:
			rec.update({'ctp_account_count':len(rec.ctp_account_ids)})

	
	@api.depends('ctp_aml_ids')
	def _compute_ctp_reversed_aml(self):
		# do nothing,keep False
		return True
		

	def _search_ctp_reversed_aml(self, operator, values):
		evaluated_val = values
		if type(evaluated_val)==list:
			AML = self.search(evaluated_val)
			return [('id', operator, AML.mapped('ctp_aml_ids').ids)]
		else:
			return []
		
