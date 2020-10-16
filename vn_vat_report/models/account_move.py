from odoo import models, fields, api


class AccountMove(models.Model):
	_inherit = 'account.move'

	vat_invoice_no = fields.Char(string='VAT Invoice No.', copy=False, required=False)
	note = fields.Text(string='Note', copy=False)


	def _recompute_payment_terms_lines(self):
		''' Compute the dynamic payment term lines of the journal entry.'''
		self.ensure_one()
		in_draft_mode = self != self._origin
		today = fields.Date.context_today(self)
		self = self.with_context(force_company=self.journal_id.company_id.id)

		def _get_payment_terms_computation_date(self):
			''' Get the date from invoice that will be used to compute the payment terms.
			:param self:    The current account.move record.
			:return:        A datetime.date object.
			'''
			if self.invoice_payment_term_id:
				return self.invoice_date or today
			else:
				return self.invoice_date_due or self.invoice_date or today

		def _get_payment_terms_account(self, payment_terms_lines):
			''' Get the account from invoice that will be set as receivable / payable account.
			:param self:                    The current account.move record.
			:param payment_terms_lines:     The current payment terms lines.
			:return:                        An account.account record.
			'''
			if payment_terms_lines:
				# Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
				return payment_terms_lines[0].account_id
			elif self.partner_id:
				# Retrieve account from partner.
				if self.is_sale_document(include_receipts=True):
					return self.partner_id.property_account_receivable_id
				else:
					return self.partner_id.property_account_payable_id
			else:
				# Search new account.
				domain = [
					('company_id', '=', self.company_id.id),
					('internal_type', '=', 'receivable' if self.type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'),
				]
				return self.env['account.account'].search(domain, limit=1)

		def _compute_payment_terms(self, date, total_balance, total_amount_currency):
			''' Compute the payment terms.
			:param self:                    The current account.move record.
			:param date:                    The date computed by '_get_payment_terms_computation_date'.
			:param total_balance:           The invoice's total in company's currency.
			:param total_amount_currency:   The invoice's total in invoice's currency.
			:return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
			'''
			if self.invoice_payment_term_id:
				to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date, currency=self.currency_id)
				if self.currency_id != self.company_id.currency_id:
					# Multi-currencies.
					to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency, date_ref=date, currency=self.currency_id)
					return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
				else:
					# Single-currency.
					return [(b[0], b[1], 0.0) for b in to_compute]
			else:
				return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

		def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
			''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
			:param self:                    The current account.move record.
			:param existing_terms_lines:    The current payment terms lines.
			:param account:                 The account.account record returned by '_get_payment_terms_account'.
			:param to_compute:              The list returned by '_compute_payment_terms'.
			'''
			# As we try to update existing lines, sort them by due date.
			existing_terms_lines = existing_terms_lines.sorted(lambda line: line.date_maturity or today)
			existing_terms_lines_index = 0

			# Recompute amls: update existing line or create new one for each payment term.
			new_terms_lines = self.env['account.move.line']
			for date_maturity, balance, amount_currency in to_compute:
				if self.journal_id.company_id.currency_id.is_zero(balance) and len(to_compute) > 1:
					continue

				if existing_terms_lines_index < len(existing_terms_lines):
					# Update existing line.
					candidate = existing_terms_lines[existing_terms_lines_index]
					existing_terms_lines_index += 1
					candidate.update({
						'date_maturity': date_maturity,
						'amount_currency': -amount_currency,
						'debit': balance < 0.0 and -balance or 0.0,
						'credit': balance > 0.0 and balance or 0.0,
						'vat_in_config_id':False,
					})
				else:
					# Create new line.
					create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
					candidate = create_method({
						'name': self.invoice_payment_ref or '',
						'debit': balance < 0.0 and -balance or 0.0,
						'credit': balance > 0.0 and balance or 0.0,
						'quantity': 1.0,
						'amount_currency': -amount_currency,
						'date_maturity': date_maturity,
						'move_id': self.id,
						'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
						'account_id': account.id,
						'partner_id': self.commercial_partner_id.id,
						'exclude_from_invoice_tab': True,
						'vat_in_config_id':False,
					})
				new_terms_lines += candidate
				if in_draft_mode:
					candidate._onchange_amount_currency()
					candidate._onchange_balance()
			return new_terms_lines

		existing_terms_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
		others_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
		company_currency_id = self.company_id.currency_id
		total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
		total_amount_currency = sum(others_lines.mapped('amount_currency'))

		if not others_lines:
			self.line_ids -= existing_terms_lines
			return

		computation_date = _get_payment_terms_computation_date(self)
		account = _get_payment_terms_account(self, existing_terms_lines)
		to_compute = _compute_payment_terms(self, computation_date, total_balance, total_amount_currency)
		new_terms_lines = _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute)

		# Remove old terms lines that are no longer needed.
		self.line_ids -= existing_terms_lines - new_terms_lines

		if new_terms_lines:
			self.invoice_payment_ref = new_terms_lines[-1].name or ''
			self.invoice_date_due = new_terms_lines[-1].date_maturity

	def _recompute_tax_lines(self, recompute_tax_base_amount=False):
		''' Compute the dynamic tax lines of the journal entry.

		:param lines_map: The line_ids dispatched by type containing:
			* base_lines: The lines having a tax_ids set.
			* tax_lines: The lines having a tax_line_id set.
			* terms_lines: The lines generated by the payment terms of the invoice.
			* rounding_lines: The cash rounding lines of the invoice.
		'''
		self.ensure_one()
		in_draft_mode = self != self._origin

		def _serialize_tax_grouping_key(grouping_dict):
			''' Serialize the dictionary values to be used in the taxes_map.
			:param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
			:return: A string representing the values.
			'''
			return '-'.join(str(v) for v in grouping_dict.values())

		def _compute_base_line_taxes(base_line):
			''' Compute taxes amounts both in company currency / foreign currency as the ratio between
			amount_currency & balance could not be the same as the expected currency rate.
			The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
			:param base_line:   The account.move.line owning the taxes.
			:return:            The result of the compute_all method.
			'''
			move = base_line.move_id

			if move.is_invoice(include_receipts=True):
				handle_price_include = True
				sign = -1 if move.is_inbound() else 1
				quantity = base_line.quantity
				if base_line.currency_id:
					price_unit_foreign_curr = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
					price_unit_comp_curr = base_line.currency_id._convert(price_unit_foreign_curr, move.company_id.currency_id, move.company_id, move.date)
				else:
					price_unit_foreign_curr = 0.0
					price_unit_comp_curr = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
				tax_type = 'sale' if move.type.startswith('out_') else 'purchase'
				is_refund = move.type in ('out_refund', 'in_refund')
			else:
				handle_price_include = False
				quantity = 1.0
				price_unit_foreign_curr = base_line.amount_currency
				price_unit_comp_curr = base_line.balance
				tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
				is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)

			balance_taxes_res = base_line.tax_ids._origin.compute_all(
				price_unit_comp_curr,
				currency=base_line.company_currency_id,
				quantity=quantity,
				product=base_line.product_id,
				partner=base_line.partner_id,
				is_refund=is_refund,
				handle_price_include=handle_price_include,
			)

			if move.type == 'entry':
				repartition_field = is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids'
				repartition_tags = base_line.tax_ids.mapped(repartition_field).filtered(lambda x: x.repartition_type == 'base').tag_ids
				tags_need_inversion = (tax_type == 'sale' and not is_refund) or (tax_type == 'purchase' and is_refund)
				if tags_need_inversion:
					balance_taxes_res['base_tags'] = base_line._revert_signed_tags(repartition_tags).ids
					for tax_res in balance_taxes_res['taxes']:
						tax_res['tag_ids'] = base_line._revert_signed_tags(self.env['account.account.tag'].browse(tax_res['tag_ids'])).ids

			if base_line.currency_id:
				# Multi-currencies mode: Taxes are computed both in company's currency / foreign currency.
				amount_currency_taxes_res = base_line.tax_ids._origin.compute_all(
					price_unit_foreign_curr,
					currency=base_line.currency_id,
					quantity=quantity,
					product=base_line.product_id,
					partner=base_line.partner_id,
					is_refund=self.type in ('out_refund', 'in_refund'),
					handle_price_include=handle_price_include,
				)

				if move.type == 'entry':
					repartition_field = is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids'
					repartition_tags = base_line.tax_ids.mapped(repartition_field).filtered(lambda x: x.repartition_type == 'base').tag_ids
					tags_need_inversion = (tax_type == 'sale' and not is_refund) or (tax_type == 'purchase' and is_refund)
					if tags_need_inversion:
						balance_taxes_res['base_tags'] = base_line._revert_signed_tags(repartition_tags).ids
						for tax_res in balance_taxes_res['taxes']:
							tax_res['tag_ids'] = base_line._revert_signed_tags(self.env['account.account.tag'].browse(tax_res['tag_ids'])).ids

				for b_tax_res, ac_tax_res in zip(balance_taxes_res['taxes'], amount_currency_taxes_res['taxes']):
					tax = self.env['account.tax'].browse(b_tax_res['id'])
					b_tax_res['amount_currency'] = ac_tax_res['amount']

					# A tax having a fixed amount must be converted into the company currency when dealing with a
					# foreign currency.
					if tax.amount_type == 'fixed':
						b_tax_res['amount'] = base_line.currency_id._convert(b_tax_res['amount'], move.company_id.currency_id, move.company_id, move.date)

			return balance_taxes_res

		taxes_map = {}

		# ==== Add tax lines ====
		to_remove = self.env['account.move.line']
		for line in self.line_ids.filtered('tax_repartition_line_id'):
			grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
			grouping_key = _serialize_tax_grouping_key(grouping_dict)
			if grouping_key in taxes_map:
				# A line with the same key does already exist, we only need one
				# to modify it; we have to drop this one.
				to_remove += line
			else:
				taxes_map[grouping_key] = {
					'tax_line': line,
					'balance': 0.0,
					'amount_currency': 0.0,
					'tax_base_amount': 0.0,
					'grouping_dict': False,
				}
		self.line_ids -= to_remove

		# ==== Mount base lines ====
		for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
			# Don't call compute_all if there is no tax.
			if not line.tax_ids:
				line.tag_ids = [(5, 0, 0)]
				continue

			compute_all_vals = _compute_base_line_taxes(line)

			# Assign tags on base line
			line.tag_ids = compute_all_vals['base_tags']

			tax_exigible = True
			for tax_vals in compute_all_vals['taxes']:
				grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
				grouping_key = _serialize_tax_grouping_key(grouping_dict)

				tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
				tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

				if tax.tax_exigibility == 'on_payment':
					tax_exigible = False

				taxes_map_entry = taxes_map.setdefault(grouping_key, {
					'tax_line': None,
					'balance': 0.0,
					'amount_currency': 0.0,
					'tax_base_amount': 0.0,
					'grouping_dict': False,
				})
				taxes_map_entry['balance'] += tax_vals['amount']
				taxes_map_entry['amount_currency'] += tax_vals.get('amount_currency', 0.0)
				taxes_map_entry['tax_base_amount'] += tax_vals['base']
				taxes_map_entry['grouping_dict'] = grouping_dict
			line.tax_exigible = tax_exigible

		# ==== Process taxes_map ====
		for taxes_map_entry in taxes_map.values():
			# Don't create tax lines with zero balance.
			if self.currency_id.is_zero(taxes_map_entry['balance']) and self.currency_id.is_zero(taxes_map_entry['amount_currency']):
				taxes_map_entry['grouping_dict'] = False

			tax_line = taxes_map_entry['tax_line']
			tax_base_amount = -taxes_map_entry['tax_base_amount'] if self.is_inbound() else taxes_map_entry['tax_base_amount']

			if not tax_line and not taxes_map_entry['grouping_dict']:
				continue
			elif tax_line and recompute_tax_base_amount:
				tax_line.tax_base_amount = tax_base_amount
			elif tax_line and not taxes_map_entry['grouping_dict']:
				# The tax line is no longer used, drop it.
				self.line_ids -= tax_line
			elif tax_line:
				tax_line.update({
					'amount_currency': taxes_map_entry['amount_currency'],
					'debit': taxes_map_entry['balance'] > 0.0 and taxes_map_entry['balance'] or 0.0,
					'credit': taxes_map_entry['balance'] < 0.0 and -taxes_map_entry['balance'] or 0.0,
					'tax_base_amount': tax_base_amount,
					'vat_in_config_id':line.vat_in_config_id.id,
				})
			else:
				create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
				tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
				tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)
				tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
				tax_line = create_method({
					'name': tax.name,
					'move_id': self.id,
					'partner_id': line.partner_id.id,
					'company_id': line.company_id.id,
					'company_currency_id': line.company_currency_id.id,
					'quantity': 1.0,
					'date_maturity': False,
					'amount_currency': taxes_map_entry['amount_currency'],
					'debit': taxes_map_entry['balance'] > 0.0 and taxes_map_entry['balance'] or 0.0,
					'credit': taxes_map_entry['balance'] < 0.0 and -taxes_map_entry['balance'] or 0.0,
					'tax_base_amount': tax_base_amount,
					'exclude_from_invoice_tab': True,
					'tax_exigible': tax.tax_exigibility == 'on_invoice',
					'vat_in_config_id':line.vat_in_config_id.id,
					**taxes_map_entry['grouping_dict'],
				})

			if in_draft_mode:
				tax_line._onchange_amount_currency()
				tax_line._onchange_balance()
	

	def action_invoice_open(self):
		""" Extend action_invoice_open() """
		super().action_invoice_open()
		if self.journal_id.type == 'purchase' and self.move_id:
			self.move_id.ref = self.vat_invoice_no
			for aml in self.move_id.line_ids:
				for line in self.invoice_line_ids:
					if aml.product_id and aml.product_id == line.product_id:
						aml.vat_in_config_id = line.vat_in_config_id.id

	@api.model
	def _get_tax_grouping_key_from_tax_line(self, tax_line):
		''' Create the dictionary based on a tax line that will be used as key to group taxes together.
		/!\ Must be consistent with '_get_tax_grouping_key_from_base_line'.
		:param tax_line:    An account.move.line being a tax line (with 'tax_repartition_line_id' set then).
		:return:            A dictionary containing all fields on which the tax will be grouped.
		'''
		res = super()._get_tax_grouping_key_from_tax_line(tax_line)
		if self.type in ('in_invoice','in_refund'):

			res.update({'vat_in_config_id':tax_line.vat_in_config_id.id})
		return res
	
	@api.model
	def _get_tax_grouping_key_from_base_line(self, base_line, tax_vals):
		res = super()._get_tax_grouping_key_from_base_line(base_line, tax_vals)
		if self.type in ('in_invoice','in_refund'):
			res.update({'vat_in_config_id':base_line.vat_in_config_id.id})

		return res

class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'

	date = fields.Date(related='move_id.date', store=True)
	vat_in_config_id = fields.Many2one('vat.in.configuration', string='Purchased VAT Category')
	
	@api.onchange('amount_currency','vat_in_config_id', 'currency_id', 'debit', 'credit', 'tax_ids', 'account_id')
	def _onchange_mark_recompute_taxes(self):
		''' Recompute the dynamic onchange based on taxes.
		If the edited line is a tax line, don't recompute anything as the user must be able to
		set a custom value.
		'''
		for line in self:
			if not line.tax_repartition_line_id:
				line.recompute_tax_line = True
	
	def _recompute_tax_lines(self, recompute_tax_base_amount=False):
		''' Compute the dynamic tax lines of the journal entry.

		:param lines_map: The line_ids dispatched by type containing:
			* base_lines: The lines having a tax_ids set.
			* tax_lines: The lines having a tax_line_id set.
			* terms_lines: The lines generated by the payment terms of the invoice.
			* rounding_lines: The cash rounding lines of the invoice.
		'''
		self.ensure_one()
		in_draft_mode = self != self._origin

		def _serialize_tax_grouping_key(grouping_dict):
			''' Serialize the dictionary values to be used in the taxes_map.
			:param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
			:return: A string representing the values.
			'''
			return '-'.join(str(v) for v in grouping_dict.values())

		def _compute_base_line_taxes(base_line):
			''' Compute taxes amounts both in company currency / foreign currency as the ratio between
			amount_currency & balance could not be the same as the expected currency rate.
			The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
			:param base_line:   The account.move.line owning the taxes.
			:return:            The result of the compute_all method.
			'''
			move = base_line.move_id

			if move.is_invoice(include_receipts=True):
				sign = -1 if move.is_inbound() else 1
				quantity = base_line.quantity
				if base_line.currency_id:
					price_unit_foreign_curr = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
					price_unit_comp_curr = base_line.currency_id._convert(price_unit_foreign_curr, move.company_id.currency_id, move.company_id, move.date)
				else:
					price_unit_foreign_curr = 0.0
					price_unit_comp_curr = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
			else:
				quantity = 1.0
				price_unit_foreign_curr = base_line.amount_currency
				price_unit_comp_curr = base_line.balance

			if move.is_invoice(include_receipts=True):
				handle_price_include = True
			else:
				handle_price_include = False

			balance_taxes_res = base_line.tax_ids._origin.compute_all(
				price_unit_comp_curr,
				currency=base_line.company_currency_id,
				quantity=quantity,
				product=base_line.product_id,
				partner=base_line.partner_id,
				is_refund=self.type in ('out_refund', 'in_refund'),
				handle_price_include=handle_price_include,
			)

			if base_line.currency_id:
				# Multi-currencies mode: Taxes are computed both in company's currency / foreign currency.
				amount_currency_taxes_res = base_line.tax_ids._origin.compute_all(
					price_unit_foreign_curr,
					currency=base_line.currency_id,
					quantity=quantity,
					product=base_line.product_id,
					partner=base_line.partner_id,
					is_refund=self.type in ('out_refund', 'in_refund'),
				)
				for b_tax_res, ac_tax_res in zip(balance_taxes_res['taxes'], amount_currency_taxes_res['taxes']):
					tax = self.env['account.tax'].browse(b_tax_res['id'])
					b_tax_res['amount_currency'] = ac_tax_res['amount']

					# A tax having a fixed amount must be converted into the company currency when dealing with a
					# foreign currency.
					if tax.amount_type == 'fixed':
						b_tax_res['amount'] = base_line.currency_id._convert(b_tax_res['amount'], move.company_id.currency_id, move.company_id, move.date)

			return balance_taxes_res

		taxes_map = {}

		# ==== Add tax lines ====
		to_remove = self.env['account.move.line']
		for line in self.line_ids.filtered('tax_repartition_line_id'):
			grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
			grouping_key = _serialize_tax_grouping_key(grouping_dict)
			if grouping_key in taxes_map:
				# A line with the same key does already exist, we only need one
				# to modify it; we have to drop this one.
				to_remove += line
			else:
				taxes_map[grouping_key] = {
					'tax_line': line,
					'balance': 0.0,
					'amount_currency': 0.0,
					'tax_base_amount': 0.0,
					'grouping_dict': False,
				}
		self.line_ids -= to_remove

		# ==== Mount base lines ====
		for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
			# Don't call compute_all if there is no tax.
			if not line.tax_ids:
				line.tag_ids = [(5, 0, 0)]
				continue

			compute_all_vals = _compute_base_line_taxes(line)

			# Assign tags on base line
			line.tag_ids = compute_all_vals['base_tags']

			tax_exigible = True
			for tax_vals in compute_all_vals['taxes']:
				grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
				grouping_key = _serialize_tax_grouping_key(grouping_dict)

				tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
				tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

				if tax.tax_exigibility == 'on_payment':
					tax_exigible = False

				taxes_map_entry = taxes_map.setdefault(grouping_key, {
					'tax_line': None,
					'balance': 0.0,
					'amount_currency': 0.0,
					'tax_base_amount': 0.0,
					'grouping_dict': False,
				})
				taxes_map_entry['balance'] += tax_vals['amount']
				taxes_map_entry['amount_currency'] += tax_vals.get('amount_currency', 0.0)
				taxes_map_entry['tax_base_amount'] += tax_vals['base']
				taxes_map_entry['grouping_dict'] = grouping_dict
			line.tax_exigible = tax_exigible

		# ==== Process taxes_map ====
		for taxes_map_entry in taxes_map.values():
			# Don't create tax lines with zero balance.
			if self.currency_id.is_zero(taxes_map_entry['balance']) and self.currency_id.is_zero(taxes_map_entry['amount_currency']):
				taxes_map_entry['grouping_dict'] = False

			tax_line = taxes_map_entry['tax_line']
			tax_base_amount = -taxes_map_entry['tax_base_amount'] if self.is_inbound() else taxes_map_entry['tax_base_amount']

			if not tax_line and not taxes_map_entry['grouping_dict']:
				continue
			elif tax_line and recompute_tax_base_amount:
				tax_line.tax_base_amount = tax_base_amount
			elif tax_line and not taxes_map_entry['grouping_dict']:
				# The tax line is no longer used, drop it.
				self.line_ids -= tax_line
			elif tax_line:
				tax_line.update({
					'amount_currency': taxes_map_entry['amount_currency'],
					'debit': taxes_map_entry['balance'] > 0.0 and taxes_map_entry['balance'] or 0.0,
					'credit': taxes_map_entry['balance'] < 0.0 and -taxes_map_entry['balance'] or 0.0,
					'tax_base_amount': tax_base_amount,
					'vat_in_config_id':base_line.vat_in_config_id.id,
				})
			else:
				create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
				tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
				tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)
				tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
				tax_line = create_method({
					'name': tax.name,
					'move_id': self.id,
					'partner_id': line.partner_id.id,
					'company_id': line.company_id.id,
					'company_currency_id': line.company_currency_id.id,
					'quantity': 1.0,
					'date_maturity': False,
					'amount_currency': taxes_map_entry['amount_currency'],
					'debit': taxes_map_entry['balance'] > 0.0 and taxes_map_entry['balance'] or 0.0,
					'credit': taxes_map_entry['balance'] < 0.0 and -taxes_map_entry['balance'] or 0.0,
					'tax_base_amount': tax_base_amount,
					'exclude_from_invoice_tab': True,
					'tax_exigible': tax.tax_exigibility == 'on_invoice',
					**taxes_map_entry['grouping_dict'],
					'vat_in_config_id':base_line.vat_in_config_id.id,
				})

			if in_draft_mode:
				tax_line._onchange_amount_currency()
				tax_line._onchange_balance()
		


	def _get_default_config(self):
		vat_in_config_id = self.env['vat.in.configuration'].search([('default_vat_in', '=', True)])
		if vat_in_config_id:
			return vat_in_config_id.id
		return False

	@api.model
	def default_get(self, fields_list):
		res = super().default_get(fields_list)
		context = self._context
		if context.get('default_type') == 'in_invoice':
			default_config_id = self._get_default_config()
			if default_config_id:
				res.update({
					'vat_in_config_id': default_config_id
				})
		return res
