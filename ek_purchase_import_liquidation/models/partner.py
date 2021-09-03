# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

from odoo import api, fields, models, _

class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'


    purchase_liq_import_count = fields.Integer(string=u'# de Importaciones', compute="_purchase_import_count")
    supplier_liq_invoice_count = fields.Integer(string=u'# de Facturas del Exterior', compute="_purchase_import_count")


    def _purchase_import_count(self):

        PurchaseOrder = self.env['ek.import.liquidation']
        Invoice = self.env['ek.import.liquidation.invoice']
        res = {}

        for partner_id in self:
            partner_id.purchase_liq_import_count = PurchaseOrder.search_count([
                    ('partner_id', 'child_of', partner_id.id), ('state', '!=', 'cancel')])
            partner_id.supplier_liq_invoice_count = Invoice.search_count([
                    ('partner_id', 'child_of', partner_id.id), ('state', '!=', 'cancel')])
