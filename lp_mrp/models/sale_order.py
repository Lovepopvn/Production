# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    """ Inherit Sale Order """

    _inherit = "sale.order"

    commitment_date = fields.Datetime('Ship Date',
                                      states={'draft': [('readonly', False)], 'sent': [('readonly', False)],
                                      'sale': [('readonly', False)]}, copy=False, readonly=True,
                                      help="This is the ship date promised to the customer. "
                                           "If set, the delivery order will be scheduled based on "
                                           "this date rather than product lead times.")
    internal_reference = fields.Char('Internal Reference', copy=False)
    employee_id_number = fields.Char('Employer Identification Number', copy=False)
    purchase_order = fields.Char('PO Number', copy=False)
    special_instructions = fields.Char('Special Instructions', copy=False)
    shipment_method = fields.Selection([
        ('AIR', 'Air'),
        ('SEA', 'SEA')
        ], string ='Shipment Method')
    fulfillment_type = fields.Selection([
        ('build_to_order', 'Build to Order'),
        ('finished_good_order', 'Finished Good Order'),
        ('purchase_to_order', 'Purchase to Order')
        ], string='Fulfillment Type', copy=False)
    order_type_id = fields.Many2one(
        comodel_name='order.type', string='Order Type', copy=False)
    urgency = fields.Selection([
        ('very_urgent', 'Very Urgent'),
        ('urgent', 'Urgent'),
        ('priority', 'Priority'),
        ('standard', 'Standard (for the MO)')
        ], string='Urgency', copy=False)
    dropship = fields.Boolean('Dropship', copy=False)
    brightpearl_warehouse_id = fields.Char('Brightpearl Warehouse ID', copy=False)
    Additional_assets = fields.Char('Additional Assets', copy=False)
    # mo_id = fields.Many2one('mrp.production', 'MO Number', copy=False)
    manufacturing_order = fields.Char('Manufacturing Order', copy=False)
    mo_ids = fields.One2many(
        comodel_name='mrp.production', inverse_name='sale_id',
        string='Manufacturing Order', copy=False)
    contain_mo = fields.Boolean(copy=False)

    def action_confirm(self):
        for sale in self:
            for line in sale.order_line:
                product = line.product_id.display_name
                mo_qty = line.product_uom_qty
                batch_size = line.product_id.lp_batch_size
                if batch_size == 0:
                    raise UserError(_('batch size for product %s is 0. Please update it' % line.product_id.display_name))
                divisible = mo_qty % batch_size
                if divisible > 0 and not self._context.get('pass_confirm'):
                    view = self.env.ref('lp_mrp.mo_divisible_wizard_view')
                    desc = "The default batchsize of Product %s is %s. \nDo you want to continue to confirm?" % (product, batch_size)
                    wiz = self.env['mo.divisible'].create({'sale_id': sale.id,
                                                            'description': desc})
                    return {
                        'name': _('Mo Divisible Confirmation'),
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'mo.divisible',
                        'views': [(view.id, 'form')],
                        'view_id': view.id,
                        'target': 'new',
                        'res_id': wiz.id,
                        'context': self.env.context,
                    }

        res = super(SaleOrder, self).action_confirm()
        for sale in self:
            mrp_obj = self.env['mrp.production']
            mrp_ids = mrp_obj.search([('origin', '=', sale.name)])
            mo_name = False
            if mrp_ids:
                for mo in mrp_ids:
                    # sale.mo_id = mrp_id.id
                    mo.sale_id = sale.id
                    mo.urgency = sale.urgency
                    if mo_name:
                        mo_name = '%s, %s' % (mo_name, mo.name)
                    else:
                        mo_name = mo.name
                self.manufacturing_order = mo_name
                self.contain_mo = True
                # check lot created from MO
                product_lot_ids = self.env['product.lot'].search([('mo_id', 'in', mrp_ids.ids)])
                if product_lot_ids:
                    picking_id = self.env['stock.picking'].search([('sale_id', '=', sale.id)],limit=1)
                    if picking_id:
                        product_lot_ids.write({
                                                'delivery_order_id': picking_id.id,
                                                'expected_delivery_date': picking_id.scheduled_date,
                                                'do_ship_date': picking_id.scheduled_date})
                        # for lot in product_lot_ids:
                        #     lot.delivery_order_id = picking_id.id
        return res

    def write(self, values):
        res = super(SaleOrder, self).write(values)
        for sale in self:
            if 'commitment_date' in values:
                commitment_date = values.get('commitment_date')
                picking_id = self.env['stock.picking'].search([('sale_id', '=', sale.id)])
                picking_id.write({'scheduled_date': commitment_date})
        return res

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def get_sale_order_line_multiline_description_sale(self, product):
        res = super(SaleOrderLine, self).get_sale_order_line_multiline_description_sale(product)
        if product.fsc_group_id or product.fsc_status_id:
            if product.fsc_group_id and product.fsc_status_id:
                res += ' - ' + product.fsc_group_id.name + ' ' + product.fsc_status_id.name
            elif product.fsc_group_id and not product.fsc_status_id:
                res += ' - ' + product.fsc_group_id.name
            elif not product.fsc_group_id and product.fsc_status_id:
                res += ' - ' + product.fsc_status_id.name
        return res