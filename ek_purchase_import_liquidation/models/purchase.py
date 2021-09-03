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

from odoo import api, fields, models , SUPERUSER_ID, _

READONLY_STATES = {
        'confirmed': [('readonly', True)],
        'approved': [('readonly', True)],
        'done': [('readonly', True)]
    }

class purchase_order_line(models.Model):
    _inherit = "purchase.order.line"

    @api.depends("order_id","order_id.is_import","product_id")
    def compute_is_import_field(self):
        for obj in self:
            if obj.order_id:
                obj.is_import = obj.order_id.is_import

    ctdad_imported = fields.Float(string="Ctdad. Importada", required=False, readonly=True, compute="_compute_pending_import", store=True)
    ctdad_pending = fields.Float(string="Ctdad. Pendiente",  required=False, readonly=True, compute="_compute_pending_import", help="Cantidad pendiente de importar", store=True)
    liquidation_line_ids = fields.One2many(comodel_name="ek.import.liquidation.line", inverse_name="purchase_line_id", string=u"Importación", required=False, help="")
    is_import = fields.Boolean(string=u"Orden de Importación",compute="compute_is_import_field", store=True)

    @api.model
    def _calc_line_base_price(self, line):
        res = super(purchase_order_line, self)._calc_line_base_price(line)
        return res * (1 - line.discount / 100.0)

    discount = fields.Float(
        string='Descuento (%)', digits_compute='Discount')

    _sql_constraints = [
        ('discount_limit', 'CHECK (discount <= 100.0)',
         'El descuento debe ser inferior al 100%.'),
    ]

    @api.depends("product_qty","liquidation_line_ids","liquidation_line_ids.state","liquidation_line_ids.product_qty")
    def _compute_pending_import(self):
        for rec in self:
            if not rec.is_import or len(rec.liquidation_line_ids) == 0:
                rec.ctdad_imported = 0
                rec.ctdad_pending = rec.product_qty
            else:
                imported = sum([p.product_qty for p in rec.liquidation_line_ids.filtered(lambda a: a.state not in ['cancel','draft'])])
                rec.ctdad_imported = imported
                diff = rec.product_qty - imported
                rec.ctdad_pending = diff > 0 and diff or 0

class purchase_order(models.Model):
    _inherit = 'purchase.order'

    is_import = fields.Boolean(string=u"Orden de Importación",  states=READONLY_STATES, help=u"Indica que esta orden de compra se realizará como importación desde el exterior")


    def button_approve_liquidation(self, force=False):
        self = self.filtered(lambda order: order._approval_allowed())
        self.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
        self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        return {}

    def button_approve(self, force=False):
        result = False
        for rec in self:

            if not rec.is_import:
                result = super(purchase_order, self).button_approve(force=force)
            else:
                result = self.button_approve_liquidation(force=force)
        return result

    def action_invoice_create(self, cr, uid, ids, context=None):
        picking_id = False
        for order in self.browse(cr, uid, ids):
            if not order.is_import:
                return super(purchase_order, self).action_invoice_create(cr, uid, ids, context=context)
        return picking_id

    @api.model
    def _prepare_inv_line(self, account_id, order_line):
        result = super(purchase_order, self)._prepare_inv_line(account_id, order_line)
        result['discount'] = order_line.discount or 0.0
        result['discount1'] = order_line.discount or 0.0
        return result

    def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, group_id, context=None):

        res = super(purchase_order, self)._prepare_order_line_move(cr, uid, order, order_line, picking_id, group_id, context=context)
        for vals in res:
            vals['price_unit'] = (vals.get('price_unit', 0.0) * (1 - (order_line.discount / 100)))
        return res