# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ek_asigned_remove_invoice(models.TransientModel):
    """Asociar regalias a viaje"""
    _name = 'ek.asigned.remove.invoice'
    _description = _(u'Asignación de Facturas Importación')

    invoice_id = fields.Many2one(comodel_name="ek.import.liquidation.invoice", string="Factura", required=False, )
    type = fields.Selection(string="Tipo", selection=[('add', 'Asignar'), ('del', 'Eliminar'), ], required=False, )


    def action_confirm(self):
        active_ids = self.env.context.get('active_ids')
        obtects = self.env['ek.import.liquidation.line'].browse(active_ids).filtered(lambda x: x.order_id.state in ['draft','calculate'])

        if len(obtects) == 0:
            raise Warning(u"Las lineas seleccionadas no cumplen las condiciones para la acción indicada.")

        for rec in obtects:
            if self.type == 'add':
                if not rec.invoice_id:
                    if self.invoice_id.partner_id.id == rec.purchase_line_id.order_id.partner_id.id:
                        rec.write({'invoice_id': self.invoice_id.id})
            else:
                if rec.invoice_id and rec.invoice_id.state == 'draft':
                    rec.write({'invoice_id': False})
