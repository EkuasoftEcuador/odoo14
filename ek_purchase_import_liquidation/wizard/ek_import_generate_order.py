# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ek_import_generate_order_line(models.TransientModel):
    _name = 'ek.import.generate.order.line'
    line_id = fields.Many2one(comodel_name='purchase.order.line', string="Linea", required=False)
    product_qty = fields.Float('Cantidad Pendiente', related="line_id.product_qty")#
    product_qty_import = fields.Float('Cantidad a Importar', required=True, default=1)
    purchase_order_id = fields.Many2one(comodel_name='purchase.order', string='Orden de Compra',related="line_id.order_id")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Proveedor", required=False,related="line_id.partner_id")#
    order_id = fields.Many2one(comodel_name="ek.import.generate.order", string="Orden", required=False, help="")
    
class ek_import_generate_order(models.TransientModel):
    """Asociar regalias a viaje"""
    _name = 'ek.import.generate.order'
    _description = _('Asociar Lineas de ordenes de compra a Importaciones')



    @api.model
    def default_get(self, fields):
        res = super(ek_import_generate_order, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        collector = False
        if active_ids:
            obtects = self.env['purchase.order.line'].browse(active_ids).filtered(lambda x: x.state != 'cancel' and x.ctdad_pending > 0)

            if len(obtects):
                lis = []
                for rec in obtects:
                    lis.append((0,0,{
                        'line_id': rec.id,
                        'product_qty_import': rec.ctdad_pending,
                        'product_qty': rec.ctdad_pending,
                        'purchase_order_id': rec.order_id.id,
                        'partner_id': rec.partner_id.id
                    }))

                res['collection_ids'] = lis


        return res

    collection_ids = new_field_ids = fields.One2many(comodel_name="ek.import.generate.order.line", inverse_name="order_id", string="Lineas")
    liq_id = fields.Many2one(comodel_name="ek.import.liquidation", string=u"Liquidación", required=True, help="")
    asigned_to_invoice = fields.Boolean(string="Asignar a Factura",  )
    invoice_id = fields.Many2one(comodel_name="ek.import.liquidation.invoice", string="Factura", required=False, )



    @api.constrains('collection_ids')
    def _check_collection_ids(self):
        for rec in self:
            if len(rec.collection_ids) == 0:
                raise ValidationError(_('No se ha definido ninguna linea para importar.'))


    def action_confirm(self):
        line_obj = self.env["ek.import.liquidation.line"]
        for rec in self:

            orders = []
            orders.append(rec.liq_id.purchase_ids.ids)
            for line in rec.collection_ids:

                line_obj.create({
                    'purchase_line_id': line.line_id.id,
                    'order_id': rec.liq_id.id,
                    'product_qty': line.product_qty_import,
                    'name': line.line_id.name,
                    'product_id': line.line_id.product_id.id,
                    'date_planned': line.line_id.date_planned,
                    'product_uom': line.line_id.product_uom and line.line_id.product_uom.id or False,
                    'tariff_id':  line.line_id.product_id.tariff_heading_id and line.line_id.product_id.tariff_heading_id.id or False,
                    'price_unit': line.line_id.price_unit,
                    'discount':   line.line_id.discount or 0.00,
                    'account_analytic_id': line.line_id.account_analytic_id and line.line_id.account_analytic_id.id or False,
                    'invoice_id': rec.invoice_id and rec.invoice_id.id or False
                })
                if line.line_id.order_id.id != rec.liq_id.purchase_id.id and line.line_id.order_id.id not in orders:
                    orders.append(line.line_id.order_id.id)
