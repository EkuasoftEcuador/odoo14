# -*- coding: utf-8 -*-
#
#    Sistema FINAMSYS
#    Copyright (C) 2016-Today Ekuasoft S.A All Rights Reserved
#    Ing. Yordany Oliva Mateos <yordanyoliva@ekuasoft.com>
#    Ing. Wendy Alvarez Chavez <wendyalvarez@ekuasoft.com>
#    EkuaSoft Software Development Group Solution
#    http://www.ekuasoft.com
#
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from odoo import api, fields, models, _
class stock_move(models.Model):
    _inherit = 'stock.move'
    liquidation_line_id = fields.Many2one(comodel_name="ek.import.liquidation.line", string=u"Linea de Importación",
                                          required=False, help="")

    '''def get_price_unit(self, cr, uid, move, context=None):
    """ Returns the unit price to store on the quant """
    if move.liquidation_line_id:
        return move.liquidation_line_id.unit_cost#price_unit

    return super(stock_move, self).get_price_unit(cr, uid, move, context=context)

@api.model
def _get_invoice_line_vals(self, move, partner, inv_type):
    res = super(stock_move, self)._get_invoice_line_vals(move, partner,inv_type)
    if move.purchase_line_id:
        res['discount'] = move.purchase_line_id.discount
    elif move.origin_returned_move_id.purchase_line_id:
        res['discount'] = \
            move.origin_returned_move_id.purchase_line_id.discount
    return res

def write(self, cr, uid, ids, vals, context=None):
    if isinstance(ids, (int, float)):
        ids = [ids]
    res = super(stock_move, self).write(cr, uid, ids, vals, context=context)

    if vals.get('state') in ['done', 'cancel']:
        po_to_check = []
        product_update_cost = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.liquidation_line_id and move.liquidation_line_id.order_id:
                order = move.liquidation_line_id.order_id
                order_id = order and order.id or False
                if order_id not in po_to_check and vals['state'] == 'cancel' and hasattr(order, "invoice_method") and order.invoice_method == 'picking':
                    po_to_check.append(order_id)

            if vals['state'] == 'done' and (move.liquidation_line_id or move.purchase_line_id):
                data_product = {
                    'product_id': move.product_id.id,
                    'product_tmpl_id': move.product_id.product_tmpl_id.id,
                    'price_unit': move.price_unit,
                    'amount_fob': 0.00,
                    'amount_cif': 0.00,
                    'is_import': False
                }


                if move.liquidation_line_id:
                    cif_rule = move.liquidation_line_id.tariff_line_ids.filtered(lambda a: a.code == 'CIF' or a.code == 'cif' or a.code == 'Cif')
                    data_product.update({
                        'is_import': True,
                        'amount_fob': move.liquidation_line_id.price_unit,
                        'amount_cif': len(cif_rule) and (cif_rule[0].amount / move.product_qty) or 0.00
                    })

                product_update_cost.append(data_product)

        # Some moves which are cancelled might be part of a PO line which is partially
        # invoiced, so we check if some PO line can be set on "invoiced = True".
        if po_to_check:
            self.pool.get('purchase.order')._set_po_lines_invoiced(cr, uid, po_to_check, context=context)
        if product_update_cost:
            self.update_product_cost_sql(cr, uid, product_update_cost, context=context)
    return res

def copy(self, cr, uid, id, default=None, context=None):
    default = default or {}
    context = context or {}
    if not default.get('split_from'):
        #we don't want to propagate the link to the purchase order line except in case of move split
        default['liquidation_line_id'] = False
    return super(stock_move, self).copy(cr, uid, id, default, context)

def attribute_price(self, cr, uid, move, context = None):
    """
        Attribute price to move, important in inter-company moves or receipts with only one partner
    """
    # The method attribute_price of the parent class sets the price to the standard product
    # price if move.price_unit is zero. We don't want this behavior in the case of a purchase
    # order since we can purchase goods which are free of charge (e.g. 5 units offered if 100
    # are purchased).
    if move.liquidation_line_id:
        return

    code = self.get_code_from_locs(cr, uid, move, context=context)
    if not move.liquidation_line_id and code == 'incoming' and not move.price_unit:
        partner = move.picking_id and move.picking_id.partner_id or False
        price = False
        # If partner given, search price in its purchase pricelist
        if partner and partner.property_product_pricelist_purchase:
            pricelist_obj = self.pool.get("product.pricelist")
            pricelist = partner.property_product_pricelist_purchase.id
            price = pricelist_obj.price_get(cr, uid, [pricelist],
                                            move.product_id.id, move.product_uom_qty, partner.id, {
                                                'uom':  move.product_uom.id,
                                                'date': move.date,
                                            })[pricelist]
            if price:
                return self.write(cr, uid, [move.id], {'price_unit': price}, context=context)
    super(stock_move, self).attribute_price(cr, uid, move, context=context)

def update_product_cost_sql(self, cr, uid, data=[], context=None):
    SQL=""
    flag = False
    for dt in data:
        if dt.get('is_import', False):
            SQL+= "UPDATE product_product SET last_cost = %s " \
                  ",amount_fob = %s, amount_cif = %s" \
                  "WHERE id=%s;" % (dt['price_unit'],dt['amount_fob'],dt['amount_cif'],dt['product_id'])



        else:
            SQL += "UPDATE product_product SET last_cost = %s WHERE id=%s;" % (dt['price_unit'], dt['product_id'])
        flag=True

    if flag:
        cr.execute(SQL)
        
'''