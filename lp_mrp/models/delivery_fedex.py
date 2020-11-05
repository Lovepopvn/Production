# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import time
import math
import io
import itertools
import functools

from PyPDF2.pdf import PdfFileReader, PdfFileWriter, PageObject
from odoo import api, models, fields, _, tools
from contracts import contract
from odoo.exceptions import UserError
from odoo.tools import pdf

from .fedex_shipping_request import FedexRequest

_logger = logging.getLogger(__name__)

# Why using standardized ISO codes? It's way more fun to use made up codes...
# https://www.fedex.com/us/developer/WebHelp/ws/2014/dvg/WS_DVG_WebHelp/Appendix_F_Currency_Codes.htm
FEDEX_CURR_MATCH = {
    u'UYU': u'UYP',
    u'XCD': u'ECD',
    u'MXN': u'NMP',
    u'KYD': u'CID',
    u'CHF': u'SFR',
    u'GBP': u'UKL',
    u'IDR': u'RPA',
    u'DOP': u'RDD',
    u'JPY': u'JYE',
    u'KRW': u'WON',
    u'SGD': u'SID',
    u'CLP': u'CHP',
    u'JMD': u'JAD',
    u'KWD': u'KUD',
    u'AED': u'DHS',
    u'TWD': u'NTD',
    u'ARS': u'ARN',
    u'LVL': u'EURO',
}

FEDEX_STOCK_TYPE = [
    ('PAPER_4X6', 'PAPER_4X6'),
    ('PAPER_4X8', 'PAPER_4X8'),
    ('PAPER_4X9', 'PAPER_4X9'),
    ('PAPER_7X4.75', 'PAPER_7X4.75'),
    ('PAPER_8.5X11_BOTTOM_HALF_LABEL', 'PAPER_8.5X11_BOTTOM_HALF_LABEL'),
    ('PAPER_8.5X11_TOP_HALF_LABEL', 'PAPER_8.5X11_TOP_HALF_LABEL'),
    ('PAPER_LETTER', 'PAPER_LETTER'),
    ('STOCK_4X6', 'STOCK_4X6'),
    ('STOCK_4X6.75_LEADING_DOC_TAB', 'STOCK_4X6.75_LEADING_DOC_TAB'),
    ('STOCK_4X6.75_TRAILING_DOC_TAB', 'STOCK_4X6.75_TRAILING_DOC_TAB'),
    ('STOCK_4X8', 'STOCK_4X8'),
    ('STOCK_4X9_LEADING_DOC_TAB', 'STOCK_4X9_LEADING_DOC_TAB'),
    ('STOCK_4X9_TRAILING_DOC_TAB', 'STOCK_4X9_TRAILING_DOC_TAB')
]

def _convert_curr_fdx_iso(code):
    curr_match = {v: k for k, v in FEDEX_CURR_MATCH.items()}
    return curr_match.get(code, code)

def _convert_curr_iso_fdx(code):
    return FEDEX_CURR_MATCH.get(code, code)

class ProviderFedex(models.Model):
    _inherit = 'delivery.carrier'

    fedex_duty_payment = fields.Selection(
        selection_add=[ ('THIRD_PARTY', 'Third Party')],
        required=True, default="THIRD_PARTY")
    fedex_bill_account_number = fields.Char(string="Billing Account Number",
                                        groups="base.group_system")
    
    @staticmethod
    @contract(page=PageObject, returns=PageObject)
    def __convert_page_to_correct_paper_size(page):
        """
            Returns a new page from the given L{page} with its content shifted from the top of the page (to
            account for the custom paper the fedex printer uses).
        """
        margin_top, crop_bottom = -64., 80
        new_page = PageObject.createBlankPage(None,
                page.mediaBox.getWidth(),
                page.mediaBox.getHeight() - crop_bottom,  # cropping the page
                                        )
        new_page.mergeScaledTranslatedPage(
                                            page,
                                            1.,  # keeping the scale of the page the same
                                            0,
                                            margin_top - crop_bottom,  # moving the content down after cropping
                                            )
        return new_page
    
    def _get_real_price_currency(self, lot, product, rule_id, qty, uom, pricelist_id):
        """Retrieve the price before applying the pricelist
            :param obj product: object of current product record
            :parem float qty: total quentity of product
            :param tuple price_and_rule: tuple(price, suitable_rule) coming from pricelist computation
            :param obj uom: unit of measure of current order line
            :param integer pricelist_id: pricelist id of sales order"""
        PricelistItem = self.env['product.pricelist.item']
        field_name = 'lst_price'
        currency_id = None
        product_currency = None
        if rule_id:
            pricelist_item = PricelistItem.browse(rule_id)
            if pricelist_item.pricelist_id.discount_policy == 'without_discount':
                while pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id and pricelist_item.base_pricelist_id.discount_policy == 'without_discount':
                    price, rule_id = pricelist_item.base_pricelist_id.with_context(uom=uom.id).get_product_price_rule(product, qty, lot.partner_id)
                    pricelist_item = PricelistItem.browse(rule_id)

            if pricelist_item.base == 'standard_price':
                field_name = 'standard_price'
            if pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id:
                field_name = 'price'
                product = product.with_context(pricelist=pricelist_item.base_pricelist_id.id)
                product_currency = pricelist_item.base_pricelist_id.currency_id
            currency_id = pricelist_item.pricelist_id.currency_id

        product_currency = product_currency or(product.company_id and product.company_id.currency_id) or self.env.company.currency_id
        if not currency_id:
            currency_id = product_currency
            cur_factor = 1.0
        else:
            if currency_id.id == product_currency.id:
                cur_factor = 1.0
            else:
                cur_factor = currency_id._get_conversion_rate(product_currency, currency_id, self.company_id or self.env.company, lot.create_date or fields.Date.today())

        product_uom = self.env.context.get('uom') or product.uom_id.id
        if uom and uom.id != product_uom:
            # the unit price is in a different uom
            uom_factor = uom._compute_price(1.0, product.uom_id)
        else:
            uom_factor = 1.0

        return product[field_name] * uom_factor * cur_factor, currency_id
    
    def _get_price(self, lot, pricelist_id):
        product_uom = lot.product_id.uom_id
        product = lot.product_id.with_context(
            lang=lot.partner_id.lang,
            partner=lot.partner_id,
            quantity=lot.number_of_items,
            date=lot.create_date,
            pricelist=pricelist_id.id,
            uom=product_uom.id
        )
        
        if pricelist_id.discount_policy == 'with_discount':
            return product.with_context(pricelist=pricelist_id.id).price
        product_context = dict(self.env.context, partner_id=lot.partner_id.id, date=lot.create_date, uom=product_uom.id)

        final_price, rule_id = pricelist_id.with_context(product_context).get_product_price_rule(lot.product_id, lot.number_of_items or 1.0, lot.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, lot.number_of_items, product_uom, pricelist_id.id)
        if currency != pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, pricelist_id.currency_id,
                lot.company_id or self.env.company, lot.create_date or fields.Date.today())
        return max(base_price, final_price)

    def fedex_send_shipping_wave(self, shipping_wave):
        res = []

        for shipping in shipping_wave:

            srm = FedexRequest(self.log_xml, request_type="shipping", prod_environment=self.prod_environment)
            superself = self.sudo()
            srm.web_authentication_detail(superself.fedex_developer_key, superself.fedex_developer_password)
            srm.client_detail(superself.fedex_account_number, superself.fedex_meter_number)

            srm.transaction_detail(shipping.id)

            package_type = shipping.product_lot_ids and shipping.product_lot_ids[0].packaging_id.shipper_package_code or self.fedex_default_packaging_id.shipper_package_code
            srm.shipment_request(self.fedex_droppoff_type, self.fedex_service_type, package_type, self.fedex_weight_unit, self.fedex_saturday_delivery)
            srm.set_currency(_convert_curr_iso_fdx(shipping.company_id.currency_id.name))
            '''check : when in the future there is multiple warehosue we need update this function'''
            # srm.set_shipper(shipping.company_id.partner_id, shipping.delivery_order_id.picking_type_id.warehouse_id.partner_id)
            srm.set_shipper(shipping.company_id.partner_id, shipping.company_id.partner_id)
            srm.set_recipient(shipping.product_lot_ids[0].delivery_order_id.partner_id)

            # srm.shipping_charges_payment(superself.fedex_account_number)
            if superself.fedex_duty_payment in ('SENDER', 'RECIPIENT'):
                srm.shipping_charges_payment(superself.fedex_account_number, superself.fedex_duty_payment)
            else:
                srm.shipping_charges_payment(superself.fedex_bill_account_number, superself.fedex_duty_payment)

            srm.shipment_label('COMMON2D', self.fedex_label_file_type, self.fedex_label_stock_type, 'BOTTOM_EDGE_OF_TEXT_FIRST', 'SHIPPING_LABEL_FIRST')

            '''check: Binh will be confirm. take the sale order with oldest date order'''
            order = shipping.product_lot_ids[0].delivery_order_id.sale_id
            company = order.company_id or shipping.company_id or self.env.company
            sale_currency = shipping.product_lot_ids[0].mo_id.sale_id.currency_id
            order_currency = sale_currency or shipping.company_id.currency_id
            
            net_weight = self._fedex_convert_weight(shipping.weight, self.fedex_weight_unit)
            
            # Commodities for customs declaration (international shipping)
            '''check: take partner from DO'''
            if self.fedex_service_type in ['INTERNATIONAL_ECONOMY', 'INTERNATIONAL_PRIORITY'] or (shipping.product_lot_ids[0].delivery_order_id.partner_id.country_id.code == 'IN' and shipping.product_lot_ids[0].delivery_order_id.partner_id.country_id.code == 'IN'):

                commodity_currency = order_currency
                if self.env.company.pricelist_id:
                    commodity_currency = self.env.company.pricelist_id.currency_id
                total_commodities_amount = 0.0
                '''check: take partner from DO'''
                commodity_country_of_manufacture = shipping.product_lot_ids[0].delivery_order_id.location_id.company_id.country_id.code

                product_lots = []
                for lot in shipping.product_lot_ids:
                    com_desc = "[%s] %s" % (lot.product_id.default_code, lot.product_id.name)
                    if lot.product_id.fsc_group_id or lot.product_id.fsc_status_id:
                        if lot.product_id.fsc_group_id and lot.product_id.fsc_status_id:
                            com_desc += ' - ' + lot.product_id.fsc_group_id.name + ' ' + lot.product_id.fsc_status_id.name
                        elif lot.product_id.fsc_group_id and not lot.product_id.fsc_status_id:
                            com_desc += ' - ' + lot.product_id.fsc_group_id.name
                        elif not lot.product_id.fsc_group_id and lot.product_id.fsc_status_id:
                            com_desc += ' - ' + lot.product_id.fsc_status_id.name
                    # put pricelist here
                    commodity_amount = lot.product_id.list_price
                    if lot.company_id.pricelist_id:
                        pricelist_id = lot.company_id.pricelist_id
                        price = self._get_price(lot, pricelist_id)
                        commodity_amount = price
                    total_commodities_amount = (commodity_amount * lot.number_of_items)
                    head = [ovals for ovals in product_lots \
                                        if ovals['commodity_description'] == \
                                        com_desc]
                    if head:
                        weight_value = lot.product_id.weight * lot.number_of_items
                        weight_value = self._fedex_convert_weight(weight_value, self.fedex_weight_unit)
                        total_commodities_amount = head[0]['total_commodities_amount'] + total_commodities_amount
                        commodity_number_of_piece = head[0]['commodity_number_of_piece'] + 1
                        commodity_weight_value = head[0]['commodity_weight_value'] + weight_value
                        commodity_quantity = head[0]['commodity_quantity'] + lot.number_of_items
                        head[0].update({
                                    'total_commodities_amount' : total_commodities_amount,
                                    'commodity_number_of_piece' : commodity_number_of_piece,
                                    'commodity_weight_value' : commodity_weight_value,
                                    'commodity_quantity' : commodity_quantity,
                                })
                    else:
                        # Sum the no of packages; no of unit; net weight, total value
                        weight_value = lot.product_id.weight * lot.number_of_items
                        weight_value = self._fedex_convert_weight(weight_value, self.fedex_weight_unit)
                        product_lots.append({
                            'commodity_amount' : commodity_amount,
                            'total_commodities_amount' : total_commodities_amount,
                            'commodity_description' : com_desc,
                            'commodity_number_of_piece' : 1,
                            'commodity_weight_units' : self.fedex_weight_unit,
                            'commodity_weight_value' : weight_value,
                            'commodity_quantity' : lot.number_of_items,
                            'commodity_quantity_units' : 'EA',
                            'commodity_harmonized_code' : lot.product_id.hs_code or '',
                        })

                commodities_amount_total = 0
                for line in product_lots:
                    commodity_amount = line['commodity_amount']
                    total_commodities_amount = line['total_commodities_amount']
                    commodity_description = line['commodity_description']
                    commodity_number_of_piece = line['commodity_number_of_piece']
                    commodity_weight_units = line['commodity_weight_units']
                    commodity_weight_value = line['commodity_weight_value']
                    commodity_quantity = line['commodity_quantity']
                    commodity_quantity_units = line['commodity_quantity_units']
                    commodity_harmonized_code = line['commodity_harmonized_code']
                    srm.commodities(_convert_curr_iso_fdx(commodity_currency.name), commodity_amount, commodity_number_of_piece, commodity_weight_units, commodity_weight_value, commodity_description, commodity_country_of_manufacture, commodity_quantity, commodity_quantity_units, commodity_harmonized_code)
                    commodities_amount_total += line['total_commodities_amount']

                invoice_num = shipping.name
                srm.customs_value(_convert_curr_iso_fdx(commodity_currency.name), commodities_amount_total, "NON_DOCUMENTS", invoice_num)
                '''check: will use company address'''
                if superself.fedex_duty_payment in ('SENDER', 'RECIPIENT'):
                    srm.duties_payment(shipping.company_id.partner_id, superself.fedex_account_number, superself.fedex_duty_payment)
                else:
                    srm.duties_payment(shipping.product_lot_ids[0].delivery_order_id.partner_id, superself.fedex_bill_account_number, superself.fedex_duty_payment)
                
                send_etd = self.env['ir.config_parameter'].sudo().get_param("delivery_fedex.send_etd")
                srm.commercial_invoice(self.fedex_document_stock_type, invoice_num, send_etd)

            lots_count = len(shipping.product_lot_ids) or 1

            '''check'''
            # For india shipping courier is not accepted without this details in label.
            # po_number = order.display_name or False
            po_number = False
            dept_number = False
            # if shipping.partner_id.country_id.code == 'IN' and shipping.picking_type_id.warehouse_id.partner_id.country_id.code == 'IN':
            #     po_number = 'B2B' if shipping.partner_id.commercial_partner_id.is_company else 'B2C'
            #     dept_number = 'BILL D/T: SENDER'

            # TODO RIM master: factorize the following crap

            ################
            # Multipackage #
            ################
            if lots_count > 1:

                # Note: Fedex has a complex multi-piece shipping interface
                # - Each lots has to be sent in a separate request
                # - First lots is called "master" lots and holds shipping-
                #   related information, including addresses, customs...
                # - Last lots responses contains shipping price and code
                # - If a problem happens with a lots, every previous lots
                #   of the shipping has to be cancelled separately
                # (Why doing it in a simple way when the complex way exists??)

                master_tracking_id = False
                lot_labels = []
                carrier_tracking_ref = ""
                delivery_orders = []

                for sequence, lots in enumerate(shipping.product_lot_ids, start=1):

                    '''check: loaded container weight'''
                    package_weight = self._fedex_convert_weight(lots.loaded_container_weight, self.fedex_weight_unit)
                    '''check'''
                    packaging = lots.packaging_id
                    srm._add_package(
                        package_weight,
                        package_code=packaging.shipper_package_code,
                        package_height=math.ceil(lots.loaded_container_height),
                        package_width=math.ceil(lots.loaded_container_width),
                        package_length=math.ceil(lots.loaded_container_length),
                        # package_height=packaging.height,
                        # package_width=packaging.width,
                        # package_length=packaging.length,
                        sequence_number=sequence,
                        po_number=po_number,
                        dept_number=dept_number,
                        # reference=lots.shipper_reference,
                        inv_number=shipping.name,
                        reference=lots.name,
                    )
                    srm.set_master_package(net_weight, lots_count, master_tracking_id=master_tracking_id)
                    request = srm.process_shipment()
                    lot_name = lots.name or sequence

                    warnings = request.get('warnings_message')
                    if warnings:
                        _logger.info(warnings)

                    # First lots
                    if sequence == 1:
                        if not request.get('errors_message'):
                            master_tracking_id = request['master_tracking_id']
                            lot_labels.append((lot_name, srm.get_label()))
                            carrier_tracking_ref = request['tracking_number']

                            # if not lots.delivery_order_id.deliver_document_update:
                            #     lots.delivery_order_id.deliver_document_update = True
                            
                            if lots.delivery_order_id:
                                head = [ovals for ovals in delivery_orders \
                                        if ovals['do'] == \
                                        lots.delivery_order_id]
                                if head:
                                    tracking_num = head[0]['tracking_num']
                                    tracking_num = "%s,%s" % (tracking_num,request['tracking_number'])
                                    head[0].update({'tracking_num': tracking_num})
                                else:
                                    delivery_orders.append({
                                        'do': lots.delivery_order_id,
                                        'tracking_num': request['tracking_number']
                                    })
                        else:
                            raise UserError(request['errors_message'])

                    # Intermediary packages
                    elif sequence > 1 and sequence < lots_count:
                        if not request.get('errors_message'):
                            lot_labels.append((lot_name, srm.get_label()))
                            carrier_tracking_ref = carrier_tracking_ref + "," + request['tracking_number']
                            # if not lots.delivery_order_id.deliver_document_update:
                            #     lots.delivery_order_id.carrier_tracking_ref = carrier_tracking_ref
                            #     lots.delivery_order_id.deliver_document_update = True
                            if lots.delivery_order_id:
                                head = [ovals for ovals in delivery_orders \
                                        if ovals['do'] == \
                                        lots.delivery_order_id]
                                if head:
                                    tracking_num = head[0]['tracking_num']
                                    tracking_num = "%s,%s" % (tracking_num,request['tracking_number'])
                                    head[0].update({'tracking_num': tracking_num})
                                else:
                                    delivery_orders.append({
                                        'do': lots.delivery_order_id,
                                        'tracking_num': request['tracking_number']
                                    })
                        else:
                            raise UserError(request['errors_message'])

                    # Last lots
                    elif sequence == lots_count:
                        # recuperer le label pdf
                        if not request.get('errors_message'):
                            lot_labels.append((lot_name, srm.get_label()))

                            if _convert_curr_iso_fdx(order_currency.name) in request['price']:
                                carrier_price = request['price'][_convert_curr_iso_fdx(order_currency.name)]
                            else:
                                _logger.info("Preferred currency has not been found in FedEx response")
                                company_currency = shipping.company_id.currency_id
                                if _convert_curr_iso_fdx(company_currency.name) in request['price']:
                                    amount = request['price'][_convert_curr_iso_fdx(company_currency.name)]
                                    carrier_price = company_currency._convert(
                                        amount, order_currency, company, order.date_order or fields.Date.today())
                                else:
                                    amount = request['price']['USD']
                                    carrier_price = company_currency._convert(
                                        amount, order_currency, company, order.date_order or fields.Date.today())

                            carrier_tracking_ref = carrier_tracking_ref + "," + request['tracking_number']
                            # if not lots.delivery_order_id.deliver_document_update:
                            #     lots.delivery_order_id.carrier_tracking_ref = carrier_tracking_ref
                            #     lots.delivery_order_id.deliver_document_update = True
                            if lots.delivery_order_id:
                                head = [ovals for ovals in delivery_orders \
                                        if ovals['do'] == \
                                        lots.delivery_order_id]
                                if head:
                                    tracking_num = head[0]['tracking_num']
                                    tracking_num = "%s,%s" % (tracking_num,request['tracking_number'])
                                    head[0].update({'tracking_num': tracking_num})
                                else:
                                    delivery_orders.append({
                                        'do': lots.delivery_order_id,
                                        'tracking_num': request['tracking_number']
                                    })

                            logmessage = _("Shipment created into Fedex<br/>"
                                           "<b>Tracking Numbers:</b> %s<br/>"
                                           "<b>Packages:</b> %s") % (carrier_tracking_ref, ','.join([pl[0] for pl in lot_labels]))
                            lot_label_data = [pl[1] for pl in lot_labels]
                            labels_iterator = iter(map(io.BytesIO, lot_label_data))
                            first_label = next(labels_iterator)
                            writer = PdfFileWriter()
                            new_reader = functools.partial(PdfFileReader, strict=False, overwriteWarnings=False)
                            for reader in map(new_reader, labels_iterator):
                                for n in range(reader.getNumPages()):
                                    page = reader.getPage(n)
                                    new_page = self.__convert_page_to_correct_paper_size(page)
                                    writer.addPage(new_page)
                            first_label_reader = new_reader(first_label)

                            for idx in itertools.chain(reversed((0,)), range(1, 5,),):
                                page = first_label_reader.getPage(idx)
                                new_page = self.__convert_page_to_correct_paper_size(page)
                                writer.insertPage(page, 0)
                            
                            output_stream = io.BytesIO()
                            writer.write(output_stream)
                            attachment = []
                            attachment.append(output_stream.getvalue())
                            
                            if self.fedex_label_file_type != 'PDF':
                                attachments = [('LabelFedex-%s.%s' % (pl[0], self.fedex_label_file_type), pl[1]) for pl in lot_labels]
                            if self.fedex_label_file_type == 'PDF':
                                ship_label_name = "Shipping Label %s.pdf" % shipping.name
                                attachments = [(ship_label_name, pdf.merge_pdf(attachment))]
                            shipping.message_post(body=logmessage, attachments=attachments)
                            for pick in shipping.delivery_order_ids:
                                pick.message_post(body=logmessage, attachments=attachments)
                            shipping_data = {'exact_price': carrier_price,
                                             'tracking_number': carrier_tracking_ref}
                            res = res + [shipping_data]
                        else:
                            raise UserError(request['errors_message'])
                shipping.master_tracking_reference = master_tracking_id
                if len(delivery_orders) > 1:
                    for do in delivery_orders:
                        delivery = do['do']
                        tracking_num = do['tracking_num']
                        delivery.carrier_tracking_ref = tracking_num
                        delivery.carrier_id = shipping.carrier_id.id
            
            # TODO RIM handle if a lots is not accepted (others should be deleted)
            
            ###############
            # One lots #
            ###############
            elif lots_count == 1:
                packaging = shipping.product_lot_ids[:1].packaging_id or shipping.carrier_id.fedex_default_packaging_id
                lots = shipping.product_lot_ids[:1]
                srm._add_package(
                    net_weight,
                    package_code=packaging.shipper_package_code,
                    package_height=math.ceil(lots.loaded_container_height),
                    package_width=math.ceil(lots.loaded_container_width),
                    package_length=math.ceil(lots.loaded_container_length),
                    # package_height=packaging.height,
                    # package_width=packaging.width,
                    # package_length=packaging.length,
                    po_number=po_number,
                    dept_number=dept_number,
                    # reference=lots.shipper_reference,
                    inv_number=shipping.name,
                    reference=lots.name,
                )
                srm.set_master_package(net_weight, 1)

                # Ask the shipping to fedex
                request = srm.process_shipment()

                warnings = request.get('warnings_message')
                if warnings:
                    _logger.info(warnings)

                if not request.get('errors_message'):

                    if _convert_curr_iso_fdx(order_currency.name) in request['price']:
                        carrier_price = request['price'][_convert_curr_iso_fdx(order_currency.name)]
                    else:
                        _logger.info("Preferred currency has not been found in FedEx response")
                        company_currency = shipping.company_id.currency_id
                        if _convert_curr_iso_fdx(company_currency.name) in request['price']:
                            amount = request['price'][_convert_curr_iso_fdx(company_currency.name)]
                            carrier_price = company_currency._convert(
                                amount, order_currency, company, order.date_order or fields.Date.today())
                        else:
                            amount = request['price']['USD']
                            carrier_price = company_currency._convert(
                                amount, order_currency, company, order.date_order or fields.Date.today())

                    shipping.master_tracking_reference = request['master_tracking_id']
                    carrier_tracking_ref = request['tracking_number']
                    logmessage = (_("Shipment created into Fedex <br/> <b>Tracking Number : </b>%s") % (carrier_tracking_ref))

                    fedex_labels = [('LabelFedex-%s-%s.%s' % (carrier_tracking_ref, index, self.fedex_label_file_type), label)
                                    for index, label in enumerate(srm._get_labels(self.fedex_label_file_type))]
                    shipping.message_post(body=logmessage, attachments=fedex_labels)
                    shipping_data = {'exact_price': carrier_price,
                                     'tracking_number': carrier_tracking_ref}
                    res = res + [shipping_data]
                else:
                    raise UserError(request['errors_message'])

            ##############
            # No lots #
            ##############
            else:
                raise UserError(_('No Product Lot for this shipping'))
            # if self.return_label_on_delivery:
            #     self.get_return_label(shipping, tracking_number=request['tracking_number'], origin_date=request['date'])
            commercial_invoice = srm.get_document()
            if commercial_invoice:
                commercial_inv_name = "Commercial Invoice %s.pdf" % shipping.name
                fedex_documents = [(commercial_inv_name, commercial_invoice)]
                shipping.message_post(body='Fedex Documents', attachments=fedex_documents)
                for pick in shipping.delivery_order_ids:
                    pick.message_post(body='Fedex Documents', attachments=fedex_documents)
        return res
    
    def send_shipping_wave(self, shipping):
        ''' Send the Lots to the service provider

        :param pickings: A recordset of pickings
        :return list: A list of dictionaries (one per picking) containing of the form::
                         { 'exact_price': price,
                           'tracking_number': number }
                           # TODO missing labels per package
                           # TODO missing currency
                           # TODO missing success, error, warnings
        '''
        self.ensure_one()
        if hasattr(self, 'fedex_send_shipping_wave'):
            return getattr(self, 'fedex_send_shipping_wave')(shipping)
    
    def fedex_wave_get_tracking_link(self, wave):
        return 'https://www.fedex.com/apps/fedextrack/?action=track&trackingnumber=%s' % wave.tracking_number
