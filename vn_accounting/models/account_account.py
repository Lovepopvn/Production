import os
import csv
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AccountAccount(models.Model):
	_inherit = 'account.account'

	name = fields.Char(string='Name',translate=False,required=True)

	def _find_account_code(self, code, operator='=', mode=None):
		if mode=='childs':
			code = code+'%'
			operator = '=ilike'
		return self.env['account.account'].search([('code',operator,code)])

	def _constrains_vn_account(self, line):
		"""
		@param new_obj -> Model
		@param skips list of field to skip
		"""
		def _apply_onchange(new_obj, skips = []):
			for field_name,mthds in new_obj._onchange_methods.items():
				if field_name not in skips:
					new_obj._onchange_eval(field_name,'1',{})
			return new_obj

		
		def _create_account(data):
			
			Model = self.env['account.account']
			new_obj = Model.new(data)
			_apply_onchange(new_obj)
			new_data = new_obj._convert_to_write({name: new_obj[name] for name in new_obj._cache})
			new_record = Model.create(new_data)
			return new_record

		splited_line = line
		code = splited_line[0]
		# print(code)
		account_existing = self._find_account_code(code)
		account_ref = self.env['account.account']
		if not len(account_existing):
			parent_code = code[:-1]
			find_inherit = self._find_account_code(parent_code) + self._find_account_code(code=code,mode='childs')
			if len(find_inherit):
				account_ref = find_inherit[0]
			else:
				account_ref = self.env['account.account']
		
			if len(account_ref):
				_logger.info("Creating account %s-%s with account reference %s" % (line[0],line[1], account_ref.display_name,))
				new_account = _create_account({
					'code':line[0],
					'name':line[1],
					'user_type_id':account_ref.user_type_id.id,
				})
				pass
			else:
				# create new one
				# line[2]-->account type
				AccType = self.env['account.account.type'].search([('name','=',line[2])])
				if len(AccType):
					new_account = _create_account({
						'code':line[0],
						'name':line[1],
						'user_type_id':AccType.id,
					})
				else:
					_logger.warning("No account type found (%s) for account %s" % (line[2], line[0]+" "+line[1]))
					pass


	@api.model
	def check_vn_account(self):
		curr_dir = os.path.dirname(__file__)
		with open(os.path.join(curr_dir,'../data/vn_account_account.csv'), newline='') as csvfile:
			contents = csv.reader(csvfile)
			pos = 0
			for line in contents:
				if pos==0:
					pos+=1
					continue
				self._constrains_vn_account(line)
				pos += 1