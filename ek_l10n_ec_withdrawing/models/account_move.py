# -*- coding: utf-8 -*-
__author__ = 'yordany'
import logging
from datetime import date
from odoo import models
from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import time

class AccountMove(models.Model):
    _inherit = 'account.move'
    retention_id = fields.Many2one('account.retention', string='Doc. Retención', copy=False)


    def action_post(self):
        rec = super(AccountMove, self).action_post()
        if self.move_type == 'in_invoice':
            return self.action_in_retention_create()

        return rec

    def button_draft(self):
        rec = super(AccountMove, self).button_draft()
        if self.move_type == 'in_invoice':
            return self.action_in_retention_cancel_draft()


    def action_in_retention_cancel_draft(self):
        """
        Redefinicion de metodo para borrar la retencion asociada.
        CHECK: saber si es correcto eliminar o hacer cache del
        numero del documento.
        """
        for inv in self:
            if inv.retention_id:
                inv.retention_id.write({'state': 'draft'})
                inv.retention_id.unlink()
        return True

    def action_in_retention_create(self):
        """
        Este método genera el documento de retencion en varios escenarios
        considera casos de:
        * Generar retencion automaticamente
        * Generar retencion de reemplazo
        * Cancelar retencion generada
        """
        for inv in self:
            # if inv.create_retention_type == 'manual':
            #    continue

            wd_number = False

            #if inv.create_retention_type == 'manual':
            #    if inv.l10n_latam_manual_document_number < 0:
            #        raise UserError(_(u'El número de retención es incorrecto.'))
            #    if inv.l10n_latam_manual_document_number == 0:
            #        continue
            #    wd_number = str(inv.l10n_latam_manual_document_number).rjust(9, "0")

            if inv.retention_id:
                inv.retention_id.action_validate(wd_number)
                continue

            if inv.move_type not in ['in_invoice', 'liq_purchase']:
                continue
                #line_ids

            #line.tax_ids
            tids = [l.id for l in inv.line_ids if l.l10n_ec_type in ['withhold_income_tax', 'withhold_vat']]

            if tids and len(tids) > 0:
                _type = self.env['l10n_latam.document.type'].search([('l10n_ec_type','=','in_withhold'),('internal_type','=','invoice')],limit=1)
                if len(_type) == 0:
                    raise ValidationError(
                        u"No existe un tipo de documento que permita realizar las retenciones de proveedor.")

                withdrawing = self.env['account.retention'].create({
                    'invoice_id': inv.id,
                    'move_type': 'ret_in_invoice',
                    'type': inv.move_type,
                    'date': inv.date,
                    'company_id': inv.company_id.id,
                    'ref': inv.name,
                    'l10n_latam_document_type_id': _type.id,
                    'name': '/',
                    'journal_id': inv.journal_id.id
                })

                account_invoice_tax = self.env['account.move.line'].browse(tids)
                account_invoice_tax.write({'retention_id': withdrawing.id})
                inv.write({'retention_id': withdrawing.id})
                withdrawing.action_validate()
        return True
