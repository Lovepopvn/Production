# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from num2words import num2words

class AccountMove(models.Model):
	""" Inherit account.move """

	_inherit = "account.move"

	def action_print_je_document(self):
		return self.env.ref('lp_journal_entries_report.action_report_je_document').report_action(self)

	def number_to_currency(self, number):
		try:
			words = num2words(number, lang='vi')
		except NotImplementedError:
			return "Please update your num2words library - your version doesn't support Vietnamese." + '\n\n' + 'pip3 install num2words --upgrade'
		currency_text = words + ' đồng'
		if number == int(number):
			# there are no decimals
			currency_text += ' chẵn'

		return currency_text