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

from odoo.tools.float_utils import float_round as round
from odoo.tools.safe_eval import safe_eval as eval
from datetime import date
from odoo import models
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import time
from odoo.tools.float_utils import float_compare


READONLY_STATES = {
        'confirmed': [('readonly', True)],
        'approved': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)]
    }

STATE_SELECTION = [
        ('draft', 'Borrador'),
        ('calculate', 'Calculada'),
        ('approved', 'Aprobada'),
        ('confirmed', 'Confirmada'),
        ('except_picking', u'Excepción de envío'),
        ('done', 'Realizado'),
        ('cancel', 'Cancelado')
    ]


class ek_import_liquidation(models.Model):

    _name = 'ek.import.liquidation'
    _description = u'Liquidación de Importación'
    _inherit = ['mail.thread', 'mail.activity.mixin','sequence.mixin']
    _order = 'date  desc'

    @api.depends("amount_total", "amount_fob")
    def _compute_factor(self):
        for obj in self:
            if obj.amount_fob > 0:
                f = obj.amount_total / obj.amount_fob
                if f >= 1:
                    obj.factor = (f - 1) * 100
                else:
                    obj.factor = f * 10
            else:
                obj.factor = 0

    @api.onchange("partner_id")
    def onchange_partner_id(self):
        if self.partner_id and self.partner_id.country_id:
            self.country_id = self.partner_id.country_id.id

    def _get_picking_in(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.user.company_id.id

        types = type_obj.search([('code', '=', 'incoming'), ('company_id', '=', company_id)], limit =1)

        if not types:
            raise UserError(_('Error!'), _(u"Asegúrese de tener al menos un tipo de picking entrante definido"))

        return types[0].id

    def _get_company(self):
        return self.env.user.company_id.id

    # @api.onchange("purchase_id","purchase_ids")
    def onchange_purchase_id(self):
        for rec in self:
            if rec.purchase_id:
                lines = []

                for line in rec.purchase_id.order_line.filtered(lambda a: a.ctdad_pending > 0):
                    lines.append((0, 0, {
                        'purchase_line_id': line.id,
                        'product_qty': line.ctdad_pending,
                        'date_planned': line.date_planned,
                        'product_weight': line.product_id.weight * line.ctdad_pending,
                        'product_uom': line.product_uom.id,
                        'product_id': line.product_id.id,
                        'price_unit': line.price_unit,
                        'discount': 0.00, # line.discount or 0.00,
                        'name': line.name,
                        'state': 'draft',
                        'tariff_id': line.product_id.tariff_heading_id.id,
                        'origin': 'auto'
                    }))

                if rec.purchase_ids:
                    for purchase in rec.purchase_ids:
                        for line in purchase.order_line.filtered(lambda a: a.ctdad_pending > 0):
                            lines.append((0, 0, {
                                'purchase_line_id': line.id,
                                'product_qty': line.ctdad_pending,
                                'date_planned': line.date_planned,
                                'product_weight': line.product_id.weight * line.ctdad_pending,
                                'product_uom': line.product_uom.id,
                                'product_id': line.product_id.id,
                                'price_unit': line.price_unit,
                                'discount': 0.00, # line.discount or 0.00,
                                'name': line.name,
                                'state': 'draft',
                                'tariff_id': line.product_id.tariff_heading_id.id,
                                'origin': 'auto'

                            }))

                rec.order_line.unlink()
                rec.order_line = lines

    name = fields.Char(u'Número', required=True, readonly=False, states=READONLY_STATES, default='/')
    origin = fields.Char('Documento Origen', copy=False,
                                        help=u"Referencia del documento que generó esta liquidación de importación.")
    date = fields.Date('Fecha', required=True , states=READONLY_STATES,
                                            select=True,
                                            copy=False,default=time.strftime('%Y-%m-%d'))
    date_approve =  fields.Date(u'Fecha de Aprobación', readonly=1, select=True, copy=False,
                                        help=u"Fecha en que se ha aprobado la importación", states=READONLY_STATES)

    purchase_id = fields.Many2one("purchase.order", string="Orden de Compra", required=False, states=READONLY_STATES)
    purchase_ids = fields.Many2many("purchase.order",  relation="purchase_order_import_adicional_rel", column1="liquidation_id", column2="order_id", string="Ordenes Adicionales", required=False,
                                  states=READONLY_STATES)

    country_id = fields.Many2one("res.country", string="Pais", required=False, )

    partner_id = fields.Many2one('res.partner', string='Proveedor', required=True, change_default=True, track_visibility='always', states=READONLY_STATES)
    location_id = fields.Many2one('stock.location', string='Destino', required=True,
                                            domain=[('usage', '<>', 'view')], states=READONLY_STATES)
    amount_total = fields.Float(string=u'Total de Importación',digits='Account' ,digits_compute='Account', states=READONLY_STATES)
    amount_fob = fields.Float(string=u'Total FOB',digits='Total FOB', digits_compute='Total FOB', readonly=True, compute="_compute_amount_fob", store=True, states=READONLY_STATES)
    percent_pvp_mayor = fields.Float(string=u'Procentaje P.V.P Mayor', default=1.2)
    percent_pvp_minor = fields.Float(string=u'Procentaje P.V.P Menor', default=1.5)
    factor = fields.Float(string=u'Factor',digits='Account', digits_compute='Account', compute="_compute_factor", store=True, help=u"Porcentaje de incremento de la importación despues de gastos e impuestos", states=READONLY_STATES)

    state = fields.Selection(STATE_SELECTION, 'Estado', readonly=True,

                                             select=True, copy=False, states=READONLY_STATES, default='draft')
    validator = fields.Many2one('res.users', string='Validado Por', readonly=True, copy=False)
    notes = fields.Text(u'Términos y Condiciones', states=READONLY_STATES)

    incoterm_id = fields.Many2one('account.incoterms', string='Incoterm',
                                            help=u"Los términos comerciales internacionales son una serie de términos comerciales predefinidos utilizados en transacciones internacionales.", states=READONLY_STATES)

    company_id = fields.Many2one('res.company', string=u'Compañía', required=True, select=1,
                                states = READONLY_STATES, default=_get_company,)

    #invoice_ids = fields.Many2many("account.invoice", relation="ek_import_liquidation_invoice_rel", column1="liquidation_id", column2="invoice", string="Facturas de Proveedor", domain="['|',('liq_purchase','=','in_invoice'),('type','=','in_invoice')]")
    invoice_ids = fields.One2many("account.move", inverse_name="invoice_liquidation_id", string="Facturas de Proveedor", required=False, )

    picking_type_id = fields.Many2one('stock.picking.type', string='Entregar a',
                                            help=u"Esto determinará el tipo de operación del envío entrante",
                                            required=True, states=READONLY_STATES, default=_get_picking_in)
    related_location_id = fields.Many2one('stock.location', related="picking_type_id.default_location_dest_id",string=u"Ubicación relacionada", store=True)
    related_usage = fields.Selection(related='location_id.usage',store=True)


    type = fields.Selection(string="Tipo", selection=[('liquidation', u'Liquidación de Importación'), ('simulation', u'Simulación de Importación'), ], required=False, )

    picking_ids = fields.One2many("stock.picking", inverse_name="liquidation_id", string=u"Selección de lista", required=False, compute="_get_picking_ids",help=u"Esta es la lista de recibos que se han generado para esta orden de compra.")

    order_line = fields.One2many("ek.import.liquidation.line", inverse_name="order_id", states=READONLY_STATES, string=u"Lineas de Importación", required=False, help="")

    breakdown_expenses_ids = fields.One2many("ek.import.liquidation.breakdown.expenses", states=READONLY_STATES, inverse_name="order_id",
                            string=u"Gatos de Importación", required=False, help="")

    related_documents_ids = fields.One2many("ek.import.liquidation.related.documents", inverse_name="order_id",
                            string=u"Documentos Relacionados", states=READONLY_STATES, required=False, help="")

    #remision_guide_ids = fields.Many2many("ek.remission.guides", relation="ek_import_liquidation_remision_guide_rel", column1="import_id", column2="remision_id", string=u"Guías de Remisión", help="")

    shipment_count = fields.Integer(string=u'Envíos entrantes', compute="_count_all",  compute_sudo=True)
    shipment_count_not_cancel = fields.Integer(string=u'Envíos entrantes', compute="_count_all",  compute_sudo=True)

    def button_uptade(self):
        for rec in self:
            rec.onchange_purchase_id()

    @api.depends("picking_ids","picking_ids.state",'state')
    def _count_all(self):
        for rec in self:
            not_cancel = 0
            shipment_count = 0
            if rec.state == 'done':
                query = """
                            SELECT picking_id, po.id, p.state FROM stock_picking p, stock_move m, ek_import_liquidation_line pol, ek_import_liquidation po
                                WHERE po.id = %s
                                AND po.id = pol.order_id
                                AND pol.id = m.liquidation_line_id
                                AND m.picking_id = p.id
                                GROUP BY picking_id, po.id, p.state
                        """
                self._cr.execute(query, (rec.id,))
                picks = self._cr.fetchall()

                shipment_count = len(picks)
                for pi in picks:
                    if pi[2] != 'cancel':
                        not_cancel+=1

            rec.shipment_count_not_cancel = not_cancel
            rec.shipment_count = shipment_count


    def _get_picking_ids(self):
        res = {}
        for po_id in self:
            res[po_id.id] = []
        query = """
            SELECT picking_id, po.id FROM stock_picking p, stock_move m, ek_import_liquidation_line pol, ek_import_liquidation po
                WHERE po.id in %s
                AND po.id = pol.order_id 
                AND pol.id = m.liquidation_line_id 
                AND m.picking_id = p.id
                GROUP BY picking_id, po.id
        """
        self._cr.execute(query, (tuple(self._ids),))
        picks = self._cr.fetchall()
        for pick_id, po_id in picks:
            res[po_id].append(pick_id)
        return res

    def action_cancel(self):
        for liq in self:

            for pick in self.env['stock.picking'].search([('liquidation_id','=',liq.id)]):
                for move in pick.move_lines:
                    if pick.state == 'done':
                        raise UserWarning(
                            _(u'No se puede cancelar la importación %s.') % (liq.name),
                            _(u'Ya has recibido algunos bienes en el inventario.  '))
                pick.action_cancel()

            liq.write({'state': 'cancel'})
            liq.order_line.write({'state': 'cancel'})

        return True

    def import_related_documents(self):
        related_docs = self.env['ek.import.liquidation.related.documents']
        invoice_exclude = []
        for liq in self:
            for docs in related_docs.search([('order_id', '=', liq.id), ('invoice_id', '!=', False)]):
                invoice_exclude.append(docs.invoice_id.id)

            for move in self.env['account.move'].search([('import_liquidation_id','=',liq.id),('id','not in',invoice_exclude),('state','=','posted')]):
                if move.id not in invoice_exclude:
                    related_docs.create({
                        'invoice_id': move.id,
                        'type': False,
                        'type_doc': 'fiscal',
                        'amount': (move.amount_untaxed and abs(move.amount_untaxed) or abs(move.amount_total)),
                        'name': move.l10n_latam_document_number,
                        'date': move.invoice_date,
                        'partner_id': move.partner_id.id,
                        'apply_by_item': False,
                        'terms_id': move.terms_id.id,
                        'order_id': liq.id
                    })

        return True

    def view_picking(self):
        cr = self._cr
        #mod_obj = self.pool.get('ir.model.data')
        #dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree'))
        #action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
        pick_ids = []
        query = """
                SELECT picking_id, po.id FROM stock_picking p, stock_move m, ek_import_liquidation_line pol, ek_import_liquidation po
                    WHERE po.id = %s
                    AND po.id = pol.order_id 
                    AND pol.id = m.liquidation_line_id 
                    AND m.picking_id = p.id
                    GROUP BY picking_id, po.id
            """
        cr.execute(query, (tuple(self._ids),))
        picks = cr.fetchall()

        for pick_id, po_id in picks:
            pick_ids += [pick_id]

        # override the context to get rid of the default filtering on picking type
        action['context'] = {}
        # choose the view_mode accordingly
        if len(pick_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"

        return action



    def test_moves_done(self, cr, uid, ids, context = None):

        for purchase in self.browse(cr, uid, ids, context=context):
            for picking in purchase.picking_ids:
                if picking.state != 'done':
                    return False
        return True

    def test_moves_except(self, cr, uid, ids, context = None):
        at_least_one_canceled = False
        alldoneorcancel = True
        for purchase in self.browse(cr, uid, ids, context=context):
            for picking in purchase.picking_ids:
                if picking.state == 'cancel':
                    at_least_one_canceled = True
                if picking.state not in ['done', 'cancel']:
                    alldoneorcancel = False
        return at_least_one_canceled and alldoneorcancel

    @api.model
    def create(self, vals):
        if not 'name' in vals or not vals['name'] or vals['name'] == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('ek.import.liquidation') or '/'

        res_id = super(ek_import_liquidation, self).create(vals)
        return res_id

    @api.onchange('picking_type_id')
    def onchange_picking_type_id(self):
        for rec in self:
            if rec.picking_type_id:
                picktype = self.env["stock.picking.type"].browse(rec.picking_type_id.id)
                if picktype.default_location_dest_id:
                    rec.location_id = picktype.default_location_dest_id.id
                    rec.related_usage = picktype.default_location_dest_id.usage
                    rec.related_location_id =  picktype.default_location_dest_id.id

    @api.onchange('location_id')
    def onchange_location_id(self):
        for rec in self:
            related_usage = False
            if rec.location_id:
                related_usage = self.env['stock.location'].browse(rec.location_id.id).usage

            rec.related_usage = related_usage

    @api.onchange('incoterm_id')
    def onchange_incoterm_id(self):
        for rec in self:

            items = []
            for term in rec.incoterm_id.incoterms_terms_ids:
                items.append((0,0,{
                'terms_id': term.terms_id.id,
                'amount': 0.00,
                'is_required': term.is_required,
                'manual': False
            }))

            rec.breakdown_expenses_ids = items

    
    def action_cancel_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})
            rec.order_line.write({'state': 'draft'})

    
    def action_convert_liquidation(self):
        for rec in self:
            val = {'type': 'liquidation'}
            if rec.name == '/':
                val.update({'name': self.env['ir.sequence'].next_by_code('ek.import.liquidation') or '/'})
            rec.write(val)

    
    def purchase_confirm(self):
        for rec in self:
            rec.calculate_liq()
            rec.write({'state': 'approved'})
            rec.order_line.write({'state': 'confirmed'})


    @api.depends("order_line", "order_line.price_subtotal")
    def _compute_amount_fob(self):
        for obj in self:
            obj.amount_fob = sum(x.price_subtotal for x in obj.order_line)


    
    def calculate_liq(self):
        for rec in self:

            breakdown_expenses_ids = []
            amount_total = 0
            # RECORRER EL DETALLE YA EXISTENTE
            for line_b in rec.breakdown_expenses_ids.filtered(lambda r: r.manual == True):
                filter_manf = list(filter(lambda x: x[2]['terms_id'] == line_b.terms_id.id, breakdown_expenses_ids))
                if len(filter_manf):
                    filter_manf[0][2]['amount'] = filter_manf[0][2]['amount'] + line_b.amount
                    if line_b.terms_id.is_considered_total:
                        amount_total+=line_b.amount
                else:
                    breakdown_expenses_ids.append((0, 0, {
                        'terms_id':              line_b.terms_id.id,
                        'manual':                 True,
                        'amount':                 line_b.amount,
                        'type': line_b.terms_id.type
                    }))
                    if line_b.terms_id.is_considered_total:
                        amount_total += line_b.amount
            # RECORRER DOCUMENTOS RELACIONADOS
            for line_b in rec.related_documents_ids.filtered(lambda r: r.apply_by_item == False):
                filter_manf = list(filter(lambda x: x[2]['terms_id'] == line_b.terms_id.id, breakdown_expenses_ids))
                if len(filter_manf):
                    filter_manf[0][2]['amount'] = filter_manf[0][2]['amount'] + line_b.amount
                    if line_b.terms_id.is_considered_total:
                        amount_total += line_b.amount

                else:
                    breakdown_expenses_ids.append((0, 0, {
                        'terms_id':              line_b.terms_id.id,
                        'manual':                 False,
                        'amount':                 line_b.amount,
                        'type': line_b.terms_id.type
                    }))
                    if line_b.terms_id.is_considered_total:
                        amount_total += line_b.amount

            # RECORRER DETALLE DE DOCUMENTOS RELACIONADOS
            for doc in rec.related_documents_ids.filtered(lambda r: r.apply_by_item == True):
                for line_b in doc.lines:

                    filter_manf = list(filter(lambda x: x[2]['terms_id'] == line_b.terms_id.id, breakdown_expenses_ids))
                    if len(filter_manf):
                        filter_manf[0][2]['amount'] = filter_manf[0][2]['amount'] + line_b.price_subtotal
                        if line_b.terms_id.is_considered_total:
                            amount_total += line_b.price_subtotal
                    else:
                        breakdown_expenses_ids.append((0, 0, {
                            'terms_id': line_b.terms_id.id,
                            'manual':   False,
                            'amount':   line_b.price_subtotal,
                            'type': line_b.terms_id.type
                        }))
                        if line_b.terms_id.is_considered_total:
                            amount_total += line_b.price_subtotal

            rec.order_line.compute_sheet()
            #Reviando los valores calculados para identificar cual aplica a los totales
            tmp_fob = 0
            for item in rec.order_line:
                tmp_fob += item.price_subtotal
                for line_b in item.tariff_line_ids.filtered(lambda r: r.terms_id):

                    filter_manf = list(filter(lambda x: x[2]['terms_id'] == line_b.terms_id.id, breakdown_expenses_ids))
                    if len(filter_manf):
                        filter_manf[0][2]['amount'] = filter_manf[0][2]['amount'] + line_b.amount
                        if line_b.terms_id.is_considered_total:
                            amount_total += line_b.amount
                    else:
                        breakdown_expenses_ids.append((0, 0, {
                            'terms_id': line_b.terms_id.id,
                            'manual':   False,
                            'amount':   line_b.amount,
                            'type': line_b.terms_id.type
                        }))
                        if line_b.terms_id.is_considered_total:
                            amount_total += line_b.amount


            rec.breakdown_expenses_ids.unlink()

            if round(tmp_fob, 2) != round(rec.amount_fob, 2):
                amount_total+=tmp_fob
                rec.write({'breakdown_expenses_ids': breakdown_expenses_ids, 'state': 'calculate','amount_fob': tmp_fob,'amount_total':amount_total})
            else:
                amount_total += rec.amount_fob
                rec.write({'breakdown_expenses_ids': breakdown_expenses_ids, 'state': 'calculate',
                           'amount_total': amount_total})

    def _prepare_order_line_move(self,order, order_line, picking_id, group_id):
        product_uom =  self.env['uom.uom']
        price_unit = order_line.unit_cost

        #if order_line.product_uom.id != order_line.product_id.uom_id.id:
        #    price_unit *= order_line.product_uom.factor / order_line.product_id.uom_id.factor

        res = []
        name = order_line.name or ''
        move_template = {
            'name':             name,
            'product_id':       order_line.product_id.id,
            'product_uom':      order_line.product_uom.id,
            'date':             order_line.date_planned or order.date,
            'date_deadline':    order_line.date_planned,
            'location_id':      order.partner_id.property_stock_supplier.id,
            'location_dest_id': order.location_id.id,
            'picking_id':       picking_id.id,
            'partner_id':       order.partner_id.id,
            'state':            'draft',
            'liquidation_line_id': order_line.id,
            'purchase_line_id': order_line.purchase_line_id.id,
            'company_id':       order.company_id.id,
            'price_unit':       price_unit,
            'picking_type_id':  order.picking_type_id.id,
            'group_id':         group_id.id,
            'origin':           order.name,
            'route_ids':        order.picking_type_id.warehouse_id and [
                (6, 0, [x.id for x in order.picking_type_id.warehouse_id.route_ids])] or [],
            'warehouse_id':     order.picking_type_id.warehouse_id.id,
        }

        diff_quantity = order_line.product_qty
        for procurement in order_line.procurement_ids:
            procurement_qty = product_uom._compute_qty(procurement.product_uom.id, procurement.product_qty,
                                                       to_uom_id=order_line.product_uom.id)
            tmp = move_template.copy()
            tmp.update({
                'product_uom_qty': min(procurement_qty, diff_quantity),
                'group_id':        procurement.group_id.id or group_id,
                'group_id':  procurement.id,
                'propagate_cancel':       procurement.rule_id.propagate,
            })
            diff_quantity -= min(procurement_qty, diff_quantity)
            res.append(tmp)
        if float_compare(diff_quantity, 0.0, precision_rounding=order_line.product_uom.rounding) > 0:
            move_template['product_uom_qty'] = diff_quantity
            res.append(move_template)
        return res

    def _create_stock_moves(self,order, order_lines,new_group, picking_id = False):

        stock_move =  self.env['stock.move']
        todo_moves = []

        for order_line in order_lines:
            if order_line.state == 'cancel':
                continue
            if not order_line.product_id:
                continue

            if order_line.product_id.type in ('product', 'consu'):
                for vals in self._prepare_order_line_move(order, order_line, picking_id, new_group):
                    move = stock_move.create(vals)
                    todo_moves.append(move)

        picking_id.action_confirm()
        #todo_moves = stock_move.action_confirm(todo_moves)
        #stock_move.force_assign(cr, uid, todo_moves)

    def action_picking_create(self):
        for order in self:
            new_group = self.env["procurement.group"].create({'name': order.name, 'partner_id': order.partner_id.id})

            picking_vals = {
                'picking_type_id': order.picking_type_id.id,
                'partner_id':      order.partner_id.id,
                'group_id':        new_group.id,
                'date':            order.date,
                'origin':          order.name,
                'location_dest_id': order.location_id.id,
                'liquidation_id': order.id,
                'location_id': order.partner_id.property_stock_supplier.id
                #'move_type'
            }
            picking_id = self.env['stock.picking'].create(picking_vals)
            self._create_stock_moves(order, order.order_line,new_group, picking_id)

            #order.write({'state':'done','order_line.state':'done'})
            order.write({'state': 'done'})
            for line in order.order_line:
                line.write({'state': 'done'})
        return picking_id




class ek_import_liquidation_invoice(models.Model):
    _name = 'ek.import.liquidation.invoice'

    name = fields.Char(u"Número")
    date = fields.Date(string="Fecha", required=False, )
    date_due = fields.Date(string=u"Fecha de vencimiento", required=False, )
    reference = fields.Char(string="Referencia", required=False, )
    partner_id = fields.Many2one('res.partner',  u'Proveedor', required=False)
    note = fields.Text(string="Notas", required=False,)

    journal_id = fields.Many2one("account.journal", string="Diario", required=False, )
    import_liquidation_id = fields.Many2one("ek.import.liquidation", string=u"Importación", required=False,)
    import_line_ids = fields.One2many("ek.import.liquidation.line", inverse_name="invoice_id", string="Items", required=False, )
    amount_total = fields.Float(string="Total",  required=False,digits='Total FOB', digits_compute='Total FOB', sum="Total", readonly=True,
                          compute="compute_calculate_amount", store=True)
    state = fields.Selection(string="Estado", selection=[('draft', 'Borrador'), ('confirm', 'Confirmado'), ('cancel', 'Cancelado') ], required=False, )
    company_id = fields.Many2one('res.company',  u'Compañía', required=False, default=lambda self: self.env.user.company_id)
    is_details = fields.Boolean(string="Asiento Detallado",  help="Si se selecciona esta opción el asiento contable de la factura se realizara una linea por cada item")
    lines_count = fields.Integer(string=u'Lineas de Factura', compute="_count_all")
    move_id = fields.Many2one("account.move", string="Asiento", required=False, readonly=True)
    payment_term_id = fields.Many2one('account.payment.term', string='Plazo de pago de',help="")
    

    def onchange_partner_id(self, partner_id):
        pterm=None
        if partner_id:
            pterm = self.env['res.partner'].browse(partner_id)
        return {'value': {'payment_term_id':pterm and pterm.property_supplier_payment_term.id or None}}


    def onchange_payment_term_date_invoice(self, payment_term_id, date):
        if not date:
            date = fields.Date.context_today(self)
        if not payment_term_id:
            # To make sure the invoice due date should contain due date which is
            # entered by user when there is no payment term defined
            return {'value': {'date_due': self.date_due or date}}
        pterm = self.env['account.payment.term'].browse(payment_term_id)
        pterm_list = pterm.compute(value=1, date_ref=date)[0]
        if pterm_list:
            return {'value': {'date_due': max(line[0] for line in pterm_list)}}
        else:
            raise UserError("No tiene terminos de pago el proveedor.")
    
    @api.depends("import_line_ids")
    def _count_all(self):
        for rec in self:
            rec.lines_count = len(rec.import_line_ids)

    def view_liquidation_line(self, cr, uid, ids, context = None):

        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'ek_purchase_import_liquidation', 'import_liquidation_line_action'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)


        invoice = self.browse(cr,uid,ids,context=context)
        pick_ids = len(invoice.import_line_ids)> 0 and invoice.import_line_ids.ids or []


        # override the context to get rid of the default filtering on picking type
        action['context'] = {}
        # choose the view_mode accordingly
        if len(pick_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"

        return action

    @api.depends("import_line_ids", "import_line_ids.price_subtotal")
    def compute_calculate_amount(self):
        for rec in self:
            if len(rec.import_line_ids):
                rec.amount_total = sum([l.price_subtotal for l in rec.import_line_ids])

            else:
                rec.amount_total = 0.00



    def action_confirm(self):
        for rec in self:
            if len(rec.import_line_ids) == 0:
                raise UserError("La factura seleccionada no posee lineas de detalles.")


            journal_id = rec.journal_id and rec.journal_id.id or False
            self.create_move(rec)
        return True


    def action_cancel_draft(self):
        """
        Metodo que se ejecuta cuando el registro ha sido anulado
        y el usuario decide volver al estado borrador.
        """
        self.write({'state': 'draft'})
        return True


    def action_cancel(self):
        for rec in self:
            if rec.move_id:
                if rec.move_id.state == 'posted':
                    raise UserError(_(
                        u'No se permiten cancelar facturas con asientos contables publicados. Por favor anule antes el asiento contable correspondiente.'))
                rec.move_id.unlink()
                for line in rec.import_line_ids:
                    line.write({'invoice_id': False})
        self.write({'state': 'cancel'})

    def create_move(self, rec):
        move_line_pool = self.pool.get('account.move.line')
        account_move = self.env['account.move']

        xline = []

        ctx = dict(self._context)

        name = rec.name
        period = False
        company = rec.company_id.id

        if not period:
            period = 1 #self.env['account.period'].with_context(ctx).find(rec.date)[:1]
        journal = rec.journal_id.with_context(ctx)
        if not period or period.state == 'done':
            raise UserError(_('No existe el periodo contable o se encuentra cerrado.'))
        if not journal:
            raise UserError(_('No ha seleccionado un diario correcto.'))

        narration = rec.note or u"Factura No. %s, Importación %s" % (rec.name, rec.import_liquidation_id.name)

        total = 0
        product_account_id = False
        for line in rec.import_line_ids.filtered(lambda a: a.invoice_id and a.invoice_id.id == rec.id):
            total+=line.price_subtotal
            account_id = line.product_id.property_account_expense and line.product_id.property_account_expense.id or False
            if not account_id:
                account_id = line.product_id.categ_id and line.product_id.categ_id.property_account_expense_categ.id or False

            product_account_id = account_id
            if rec.is_details:
                xline.append((0, 0, {
                    'name':       u"Factura No. %s, Importación %s" % (rec.name, rec.import_liquidation_id.name),
                    'product_id': line.product_id.id,
                    'debit':      line.price_subtotal,
                    'account_id': account_id,
                    'credit':     0.00,
                    'ref':        rec.name,
                    'period_id':  period.id,
                    'partner_id': rec.partner_id.id,
                    'date_maturity':rec.date_due
                }))

        account_id = rec.partner_id.property_account_payable and rec.partner_id.property_account_payable.id or False
        if not rec.is_details:
            xline.append((0, 0, {
                'name':       u"Factura No. %s, Importación %s" % (rec.name, rec.import_liquidation_id.name),
                'debit':      total,
                'account_id': product_account_id,
                'credit':     0.00,
                'ref':        narration,
                'period_id':  period.id,
                'partner_id': rec.partner_id.id,
                'date_maturity':rec.date_due
            }))

        xline.append((0, 0, {
            'name':       u"Factura No. %s, Importación %s" % (rec.name, rec.import_liquidation_id.name),
            'credit':     total,
            'debit':      0.00,
            'account_id': account_id,
            'ref':        narration,
            'period_id':  period.id,
            'partner_id': rec.partner_id.id,
            'date_maturity':rec.date_due
        }))

        move_vals = {
            'ref':        u"Factura No. %s, Importación %s" % (rec.name, rec.import_liquidation_id.name),
            'line_id':    xline,
            'journal_id': rec.journal_id.id,
            'date':       rec.date,
            'period_id':  period.id,
            'narration':  narration

        }

        move = account_move.with_context(ctx).create(move_vals)
        rec.write({'move_id': move.id,'state':'confirm'})
        if journal.entry_posted:
            pass
            #move.post()

class ek_import_liquidation_line(models.Model):

    _name = 'ek.import.liquidation.line'
    _description = u'Lineas de Liquidación de Importación'


    origin = fields.Selection(string="Origen", selection=[('manual', 'Manual'), ('auto', u'Automático'), ], required=False, default='manual')
    name = fields.Text(u'Descripción', required=True)
    product_qty = fields.Float('Cantidad', digits='Product Unit of Measure',digits_compute='Product Unit of Measure',
                                        required=True, default=1)
    product_weight = fields.Float('Peso/Kg',digits_compute='Product Unit of Measure',
                               required=False, default=0.00)
    date_planned =  fields.Datetime('Fecha planificada', required=True, select=True, help=u"Fecha en la que se estima llegará la mercaderia", default = lambda self: time.strftime('%Y-%m-%d'))

    product_uom = fields.Many2one('uom.uom', string=u'U/M', required=True)
    product_id = fields.Many2one('product.product', string='Producto', domain=[('purchase_ok', '=', True)],
                                           change_default=True, required=True)
    tariff_id = fields.Many2one('ek.tariff.heading', 'Partida Arancelaria', ondelete='restrict',
                                domain=[('type', '<>', 'view')])

    '''move_ids':            fields.one2many('stock.move', 'purchase_line_id', 'Reservation', readonly=True,
                                           ondelete='set null'),'''
    adv_manual = fields.Float(string=u"% Advalorem Manual", required=False, help=u"% Manual de advaloren segun convenio aplicado.", default=-1)
    price_unit = fields.Float('FOB', required=True,digits='FOB',
                                        digits_compute='FOB')

    discount = fields.Float(string='Descuento (%)', digits_compute='Discount')
    price_subtotal = fields.Float(string='Total FOB',digits='Total FOB',digits_compute='Total FOB', compute="_amount_line", store=True)#
    tariff_subtotal = fields.Float(string='Tributos', digits_compute='Importation Tributes', digits='Importation Tributes', compute="_tariff_subtotal", store=True)
    freight_subtotal = fields.Float(string='Flete',digits='Importation Others', digits_compute='Importation Others', compute="_amount_general_subtotal", store=True)
    insurance_subtotal = fields.Float(string='Seguro',digits='Importation Others', digits_compute='Importation Others', compute="_amount_general_subtotal", store=True)
    expenses_abroad = fields.Float(string='Gastos Exteriores', digits='Importation Others',
                                      digits_compute='Importation Others',
                                      compute="_amount_general_subtotal", store=True, help="Gastos del exterior que no afectan el costo, solo para calcular impuestos de aduana.")
    expenses_subtotal = fields.Float(string='Gastos',digits='Import Expenses', digits_compute='Import Expenses', compute="_amount_general_subtotal", store=True)
    share = fields.Float(string=u'% REP', digits_compute='Importation Factor', digits='Importation Factor',
                                     compute="_amount_line_share", store=True, help=u"% de Representación es el impacto que tiene cada rubro sobre el total FOB")
    amount_total = fields.Float(string='Total Costo',digits='Total Costs of Import', digits_compute='Total Costs of Import', compute="_amount_general_total", store=True)
    factor = fields.Float(string=u'Factor', digits_compute='Account', compute="_amount_general_total",
                          store=True, help=u"Porcentaje de incremento de la importación despues de gastos e impuestos")
    unit_cost = fields.Float(string='Costo Unit.',digits='Importation Costs', digits_compute='Importation Costs', compute="_amount_general_total",store=True)
    order_id = fields.Many2one('ek.import.liquidation', string=u'Importación', select=True,ondelete='cascade')

    company_id = fields.Many2one('res.company', string=u'Compañía', related="order_id.company_id", select=1, store=True, default=lambda self: self.env.company.id)

    account_analytic_id = fields.Many2one('account.analytic.account', string=u'Cuenta Analítica')

    date_order = fields.Date(related="order_id.date", string='Fecha', readonly=True)

    state =fields.Selection(
        [('draft', 'Borrador'), ('confirmed', 'Confirmado'), ('done', 'Realizado'), ('cancel', 'Cancelado')],
        'Estado', required=True, readonly=True, copy=False, default='draft')

    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', string='Proveedor', readonly=True,
                                           store=True)

    tariff_line_ids = fields.One2many("ek.tariff.rule.line", inverse_name="line_liquidation_id",
                                        string=u"Reglas", required=False, help="")

    procurement_ids = fields.One2many('procurement.group', inverse_name='liquidation_line_id', string='Ordenes Asociadas')

    invoice_id = fields.Many2one("account.move", string="Factura", required=False, )
    purchase_line_id = fields.Many2one("purchase.order.line", string=u"Línea de orden de compra")

    #Calculos adicionales
    related_fodinfa = fields.Float(string="Valor FODINFA",  required=False, compute="_calculate_related_arancel",) #FODINFA
    related_advalorem = fields.Float(string="Valor ADVALOREM", required=False,
                                   compute="_calculate_related_arancel", )  # FODINFA
    pvp_mayor = fields.Float(string="PVP Mayor INC. IVA", required=False, help="Precio de Venta incluido iva")
    pvp_minor = fields.Float(string="P.V.P. x Menor", required=False, compute="_amount_pvp", help="Precio de Venta al por menor")



    def change_product_price(self):
        for rec in self:
            if rec.state in ['confirmed','done']:
                rec.product_id.write({'list_price': rec.pvp_mayor})

    @api.depends("pvp_mayor")
    def _amount_pvp(self):
        for obj in self:
            tax = 1.12
            #obj.pvp_mayor = ((obj.unit_cost * obj.order_id.percent_pvp_mayor) * tax)
            obj.pvp_minor = round((((obj.pvp_mayor/tax)*obj.order_id.percent_pvp_minor)*tax),0)
            #=REDONDEAR((((M6/1,12)*1,5)*1,12);0)

    @api.depends("tariff_line_ids")
    def _calculate_related_arancel(self):
        for obj in self:
            FODI = obj.tariff_line_ids.filtered(lambda a: a.code == 'FODINFA')
            obj.related_fodinfa = len(FODI) > 0 and FODI[0].amount or 0.00
            ADVA = obj.tariff_line_ids.filtered(lambda a: a.code == 'ARA')
            obj.related_advalorem = len(ADVA) > 0 and ADVA[0].amount or 0.00

    @api.model
    def create(self, vals):
        if 'origin' in vals and vals['origin'] == 'manual':
            raise UserWarning(
                            _(u'Línea [%s] Incorrecta.') % (vals['name']),
                            _(u'No se permite añadir una linea que no tenga como origen una orden de compra.'))

        res_id = super(ek_import_liquidation_line, self).create(vals)
        return res_id

    def get_calculation_lines(self, liquidation_line):
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            if category.code in localdict['categories'].dict:
                amount += localdict['categories'].dict[category.code]
            localdict['categories'].dict[category.code] = amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, pool, cr, uid, tariff_id, dict):
                self.pool = pool
                self.cr = cr
                self.uid = uid
                self.tariff_id = tariff_id
                self.dict = dict

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0


        result_dict = {}
        rules = {}
        categories_dict = {}
        blacklist = []
        liquidation_line_obj = self.env['ek.import.liquidation.line']

        obj_rule = self.env['ek.tariff.rule']
        obj_tariff_heading = self.env['ek.tariff.heading']
        cr = self._cr
        uid = self._uid
        context = self._context
        liquidation_l = liquidation_line_obj.browse(liquidation_line)


        rules_obj = BrowsableObject(self.pool, cr, uid, liquidation_l.tariff_id.id, rules)
        categories_obj = BrowsableObject(self.pool, cr, uid, liquidation_l.tariff_id.id, categories_dict)

        baselocaldict = {'categories': categories_obj,'rules': rules_obj, 'line_obj': liquidation_l}



        line = liquidation_l
        if line:


            rule_ids = obj_tariff_heading.browse(line.tariff_id.id).tariff_rule_ids


            localdict = dict(baselocaldict, line=line, tariff=line.tariff_id)

            for rule in rule_ids:

                key = rule.code + '-' + str(line.id)


                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100
                # check if the rule can be applied
                if rule.id not in blacklist and rule.satisfy_condition(localdict):
                    # compute the amount of the rule
                    amount, qty, rate = rule.compute_rule(localdict)
                    # check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                    # set/overwrite the amount computed for this rule in the localdict
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    rules[rule.code] = rule
                    # sum the amount for its salary category
                    localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                    # create/overwrite the rule in the temporary results
                    if amount == 0:
                        continue

                    result_dict[key] = {
                        'rule_id':         rule.id,
                        'line_liquidation_id': line.id,
                        'name':                   rule.name,
                        'code':                   rule.code,
                        'param':                  rule.param,
                        'terms_id':               rule.terms_id.id,
                        'category_id':            rule.category_id.id,
                        'sequence':               rule.sequence,
                        'condition_select':       rule.condition_select,
                        'condition_python':       rule.condition_python,
                        'condition_range':        rule.condition_range,
                        'condition_range_min':    rule.condition_range_min,
                        'condition_range_max':    rule.condition_range_max,
                        'amount_select':          rule.amount_select,
                        'amount_fix':             rule.amount_fix,
                        'amount_python_compute':  rule.amount_python_compute,
                        'amount_percentage':      rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'amount':                 amount,
                        'quantity':               qty,
                    }


        result = [value for code, value in result_dict.items()]
        return result

    
    def compute_sheet(self):
        slip_line_pool = self.pool.get('ek.tariff.rule')
        slip_line_employee_pool = self.pool.get('ek.tariff.rule.line')


        contract_ids = []
        for rec in self:
            rec.tariff_line_ids.unlink()

            lines = [(0, 0, line) for line in self.get_calculation_lines(rec.id)]
                     #self.pool.get('ek.import.liquidation.line').get_calculation_lines(self._cr, self._uid,rec.id,
                     #                                                             context=self._context)]


            rec.write({'tariff_line_ids': lines})
        return True

    def _calc_line_base_price(self, cr, uid, line, context = None):
        """Return the base price of the line to be used for tax calculation.

        This function can be extended by other modules to modify this base
        price (adding a discount, for example).
        """
        return line.price_unit

    def _calc_line_quantity(self, cr, uid, line, context = None):
        """Return the base quantity of the line to be used for the subtotal.

        This function can be extended by other modules to modify this base
        quantity (adding for example offers 3x2 and so on).
        """
        return line.product_qty

    @api.depends("product_id",'discount', "price_unit", "product_qty")
    def _amount_line(self):
        for obj in self:
            obj.price_subtotal = (obj.product_qty * obj.price_unit) * (1 - obj.discount / 100.0)
            if obj.product_id.weight > 0:
                obj.product_weight = obj.product_id.weight * obj.product_qty



    @api.depends("price_subtotal",'discount',"order_id","order_id.amount_fob")
    def _amount_line_share(self):

        obj_precision = self.pool.get('decimal.precision')
        #prec = obj_precision.precision_get(self._cr, self._uid, 'Importation Factor')
        for obj in self:
            if obj.order_id.amount_fob > 0:
                obj.share = obj.price_subtotal / obj.order_id.amount_fob #round(, prec)

            else:
                obj.share = 0

    @api.depends("tariff_line_ids", "tariff_line_ids.amount","price_subtotal","price_unit",'tariff_id')
    def _tariff_subtotal(self):
        for obj in self:
            obj.tariff_subtotal =  sum(x.amount for x in obj.tariff_line_ids if x.param == False and x.line_liquidation_id.id == obj.id)

    @api.depends("price_subtotal", "tariff_subtotal", "freight_subtotal", "insurance_subtotal", 'expenses_subtotal','order_id.percent_pvp_mayor')
    def _amount_general_total(self):

        for obj in self:
            obj.amount_total = obj.price_subtotal + obj.tariff_subtotal + obj.freight_subtotal + obj.insurance_subtotal + obj.expenses_subtotal
            if obj.price_subtotal > 0:
                obj.factor = obj.amount_total/obj.price_subtotal
            else:
                obj.factor = 0
            obj.unit_cost = obj.factor * obj.price_unit
            tax = 1.12
            obj.pvp_mayor = ((obj.unit_cost * obj.order_id.percent_pvp_mayor) * tax)


    @api.depends("order_id", "order_id.breakdown_expenses_ids","share")
    def _amount_general_subtotal(self):
        for obj in self:
            freight_subtotal = 0
            insurance_subtotal = 0
            expenses_subtotal = 0
            expenses_abroad = 0
            for rec in obj.order_id.breakdown_expenses_ids:

                if rec.terms_id.is_provider_assumed:
                    expenses_abroad+=rec.amount

                else:
                    if rec.type == 'freight':
                        #if obj.order_id.incoterm_id.freight_assumed_provider:
                        freight_subtotal += rec.amount
                    elif rec.type == 'insurance':
                        insurance_subtotal += rec.amount
                    elif rec.type == 'expense':
                        expenses_subtotal+=rec.amount


            obj.freight_subtotal = freight_subtotal * obj.share
            obj.insurance_subtotal = insurance_subtotal * obj.share
            obj.expenses_subtotal = expenses_subtotal * obj.share
            obj.expenses_abroad = expenses_abroad * obj.share

    def _get_uom_id(self, cr, uid, context = None):
        try:
            proxy = self.pool.get('ir.model.data')
            result = proxy.get_object_reference(cr, uid, 'product', 'product_uom_unit')
            return result[1]
        except Exception:
            return False

    @api.onchange('product_id')
    def onchange_product_id(self):

       for rec in self:
           rec.tariff_id = rec.product_id.tariff_heading_id.id
           rec.name = rec.product_id.name
           rec.product_qty = 1
           rec.product_weight = rec.product_id.weight
           rec.price_unit =  rec.last_cost


    def onchange_product_uom(self, cr, uid, ids, tariff_id, product_id, qty, uom_id,
                             partner_id, date = False,
                             name = False, price_unit = False, state = 'draft', context = None):
        """
        onchange handler of product_uom.
        """
        if context is None:
            context = {}
        if not uom_id:
            return {'value': {'price_unit': price_unit or 0.0, 'name': name or '', 'product_uom': uom_id or False}}
        context = dict(context, purchase_uom_check=True)
        return self.onchange_product_id(cr, uid, ids, tariff_id, product_id, qty, uom_id,
                                        partner_id, date=date,
                                        name=name, price_unit=price_unit, state=state, context=context)

    _sql_constraints = [
        ('discount_limit', 'CHECK (discount <= 100.0)',
         u'El descuento debe ser inferior al 100%.'),
    ]

class ek_tariff_rule_line(models.Model):


    _name = 'ek.tariff.rule.line'
    _inherit = 'ek.tariff.rule'
    _description = u'Calculo de Líneas'
    _order = 'sequence'

    line_liquidation_id = fields.Many2one("ek.import.liquidation.line", string=u"Líneas", required=False, ondelete='cascade')
    rule_id = fields.Many2one("ek.tariff.rule", string="Regla", required=False, help="")
    amount = fields.Float(string="Valor", required=False, digits='Total Costs of Rule', digits_compute='Total Costs of Rule')
    terms_id = fields.Many2one("ek.incoterms.terms", string="Aplicar A", required=False)


class ek_import_liquidation_breakdown_expenses(models.Model):
    _name = 'ek.import.liquidation.breakdown.expenses'
    _description = u'Desglose de gastos de importación'
    _order = 'sequence'
    order_id = fields.Many2one('ek.import.liquidation', string=u'Importación', select=True, ondelete='cascade')

    terms_id = fields.Many2one("ek.incoterms.terms", string="Termino", required=True)
    amount = fields.Float(string='Valor', digits_compute='Account')
    code = fields.Char(u'Código', size=64, required=False, readonly=False, related="terms_id.code", store=True)
    type = fields.Selection(string="Tipo",
                            selection=[('freight', 'Flete'), ('insurance', 'Seguro'), ('expense', 'Gasto'),
                                       ('other', 'Otros'), ('liquidation', 'Otros')], required=False, store=True, related="terms_id.type", default="other")
    sequence = fields.Integer('Orden', required=False, help=u'Úselo para organizar la secuencia de cálculo',
                              select=True, related="terms_id.sequence", store=True)
    manual = fields.Boolean(string="Manual",  default=True)
    is_required = fields.Boolean(string="Requerido")
    is_considered_total = fields.Boolean(string="Considerado en el total?", select=True, related="terms_id.is_considered_total", store=True)
    #
    #amount_type = fields.Selection(string="Tipo de monto", selection=[('value', 'Por Valor'), ('weight', 'Por Peso'), ('quantity', 'Por Cantidad'), ], required=True, default="value")

class ek_import_liquidation_type_docs(models.Model):
    _name = 'ek.import.liquidation.type.docs'
    _description = u'Tipos de Documentos de Importación'
    name = fields.Char(string="Documento", required=True, help="")


class ek_import_liquidation_related_documents(models.Model):
    _name = 'ek.import.liquidation.related.documents'
    _description = u'Desglose de documentos de importación'

    order_id = fields.Many2one('ek.import.liquidation', string=u'Importación', select=True, ondelete='cascade')

    type_doc = fields.Selection(string="Tipo de Documento",
                                selection=[('fiscal', 'Relacionado'),
                                           ('others', u'Sin Relación')],

                                required=False
                                )
    #baseImponibleReemb|baseImpGravReemb
    invoice_id = fields.Many2one("account.move", string="Documento", required=False, help="")
    voucher_id = fields.Many2one("account.move", string="Documento", required=False, help="")
    generic_document_id = fields.Many2one("ek.generic.documents", string="Documento", required=False, help="")
    type = fields.Many2one("ek.import.liquidation.type.docs", string="Tipo", required=False, help="")
    amount = fields.Float(string='Total', digits_compute='Account')
    name = fields.Char(string=u"Número", required=False, help="")
    date = fields.Date(string="Fecha", required=False, help="")
    partner_id = fields.Many2one('res.partner', string='Proveedor',change_default=True,track_visibility='always')
    lines = fields.One2many("ek.import.liquidation.related.documents.line", inverse_name="related_documents_id", string="Lineas", required=False, help="")
    apply_by_item = fields.Boolean(string="Detallar Items",  help="Permite detallar los valores por cada item")

    terms_id = fields.Many2one("ek.incoterms.terms", string="Aplicar A", required=False)

    @api.onchange("type_doc","invoice_id")
    def onchange_document_id(self):
        for res in self:
            if res.type_doc == 'fiscal' and res.invoice_id:
                invoice_pool = self.env['account.move']
                invoice = invoice_pool.browse(res.invoice_id.id)
                if invoice:
                    res.update({'amount': (invoice.amount_untaxed and abs(invoice.amount_untaxed) or abs(invoice.amount_total)), 'name': invoice.l10n_latam_document_number, 'date': invoice.invoice_date})



class ek_import_liquidation_related_documents_line(models.Model):
    _name = 'ek.import.liquidation.related.documents.line'
    _description = u'Lineas de Documentos Relacionados'


    line_invoice_id = fields.Many2one("account.move.line", string="Linea Factura", required=False, )

    name = fields.Text(u'Descripción', required=True)
    product_qty = fields.Float('Cantidad', digits_compute='Product Unit of Measure',
                               required=True, default=1)
    product_weight = fields.Float('Peso/Kg', digits_compute='Product Unit of Measure',
                                  required=False, default=0.00)

    product_uom = fields.Many2one('uom.uom', string='Unidad de Medida', required=True)
    product_id = fields.Many2one('product.product', string='Producto', domain=[('purchase_ok', '=', True)],
                                 change_default=True, required=False)

    '''price_unit = fields.Float('Precio Unitario', required=True,
                              digits_compute='Product Price'))'''


    price_subtotal = fields.Float(string='Monto', digits_compute='Account')

    related_documents_id = fields.Many2one("ek.import.liquidation.related.documents", string="Documento", required=False, help="")

    terms_id = fields.Many2one("ek.incoterms.terms", string="Aplicar A", required=False)

    def _get_uom_id(self, cr, uid, context = None):
        try:
            proxy = self.pool.get('ir.model.data')
            result = proxy.get_object_reference(cr, uid, 'product', 'product_uom_unit')
            return result[1]
        except Exception:
            return False

    @api.onchange("line_invoice_id")
    def onchange_line_invoice_id(self):
        for rec in self:
            if rec.line_invoice_id:
                rec.name = rec.line_invoice_id.name
                rec.product_qty = rec.line_invoice_id.quantity
                rec.product_uom = rec.line_invoice_id.product_uom_id and rec.line_invoice_id.product_uom_id.id or False
                rec.product_id = rec.line_invoice_id.product_id and rec.line_invoice_id.product_id.id or False
                rec.price_subtotal = abs(rec.line_invoice_id.price_subtotal)

    @api.onchange("product_id")
    def onchange_product_id(self, cr, uid, ids, product_id, qty, uom_id,
                            partner_id, date = False,
                            name = False, price_unit = False, context = None):
        for rec in self:

           rec.name = rec.product_id.name
           rec.product_qty = 1
           rec.product_weight = rec.product_id.weight

    def onchange_product_uom(self, cr, uid, ids, product_id, qty, uom_id,
                             partner_id, date = False,
                             name = False, price_unit = False, context = None):
        """
        onchange handler of product_uom.
        """
        if context is None:
            context = {}
        if not uom_id:
            return {'value': {'price_unit': price_unit or 0.0, 'name': name or '', 'product_uom': uom_id or False}}
        context = dict(context, purchase_uom_check=True)

        return self.onchange_product_id(cr, uid, ids, product_id, qty, uom_id,
                                        partner_id, date=date,
                                        name=name, price_unit=price_unit, context=context)


