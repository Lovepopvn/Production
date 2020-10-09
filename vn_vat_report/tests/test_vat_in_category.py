from odoo.tests.common import Form
from odoo.tests import SavepointCase, tagged


class TestVatInCategory(SavepointCase):
    
    def setUp(cls):
        super(TestVatInCategory, cls).setUp()
        taxes = cls.env['account.tax'].search([('type_tax_use','=','purchase')])
        tax10 = taxes.filtered(lambda r:r.name=="Thuế GTGT được khấu trừ 10%")
        tax5 = taxes.filtered(lambda r:r.name=="Thuế GTGT được khấu trừ 5%")

        cls.Vendor = cls.env['res.partner'].create({
            'name':"test Partner",
        })
        move_data = {
            'partner_id':cls.Vendor.id,
            'type':'in_invoice',

            'ref':'Testing vat in category 01',
            
        }
        tmp_bill = cls.env['account.move'].new(move_data)
        tmp_bill._onchange_eval('type','1',{})
        tmp_bill._onchange_eval('partner_id','1',{})
        InvLine = cls.env['account.move.line']
        line1 = InvLine.new({
            'move_id':tmp_bill,
            
        })
        line1._onchange_eval('move_id','1',{})
        line1.update({
            'name':'prod1 vat 1 tax 10',
            'vat_in_config_id':1,
            'price_unit':100000,
            'quantity':1,
            
        })
        line1._onchange_eval('vat_in_config_id','1',{})
        line1.update({'account_id':cls.env['account.account'].search([('code','=',1561)])})
        line1._onchange_eval('quantity','1',{})
        line1._onchange_eval('price_unit','1',{})
        line1.update({'tax_ids':[(6,0,tax10.ids)],})
        line1._onchange_eval('tax_ids','1',{})

        # lines = [(0,0,),
        # (0,0,{
        #     'name':'prod1 vat 1 tax 10',
        #     'vat_in_config_id':1,
        #     'tax_ids':[(6,0,tax5.ids)],
        #     'price_unit':100000,
        #     'quantity':1,
        # })]
        
        tmp_bill.update({'invoice_line_ids':line1})
        new_move = tmp_bill._convert_to_write(dict(tmp_bill._cache))
        # new_move['line_ids'] = [(6,0,[])]
        cls.Bill = cls.env['account.move'].create(new_move)
        
    def test_01(self):
        self.assertTrue(len(self.Bill.invoice_line_ids)==2)
        