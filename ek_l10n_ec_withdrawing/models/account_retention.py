# -*- coding: utf-8 -*-
__author__ = 'yordany'
import logging
from datetime import date
from odoo import models
from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import time

class AccountRetention(models.Model):
    _name = 'account.retention'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'sequence.mixin']
    _description = "Retenciones"
    _order = 'date desc, name desc'
    _mail_post_access = 'read'
    _check_company_auto = True
    _sequence_index = "journal_id"

    move_type = fields.Selection(selection=[
        ('ret_in_invoice', u'Retención a Proveedor'),
        ('ret_out_invoice', u'Retención de Cliente')
    ], string='Type', required=True, store=True, index=True, readonly=True, tracking=True,
        default="ret_in_invoice", change_default=True)

    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', 'Tipo de Comprobante')

    l10n_latam_parent_document_type_id = fields.Many2one('l10n_latam.document.type', 'Doc.', related='invoice_id.l10n_latam_document_type_id',)

    name = fields.Char(string='Number', copy=False, readonly=False, store=True, index=True,
                       tracking=True, default="/", states={'draft': [('readonly', False)]},)

    company_id = fields.Many2one(
        'res.company',
        u'Compañía',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user.company_id
    )

    create_retention_type = fields.Selection(
        [('auto', u'Automático'),
         ('manual', 'Manual'),
         ],
        string=u'Numerar Retención',
        required=True,
        default='auto'
    )
    tax_ids = fields.One2many(
        'account.move.line',
        'retention_id',
        'Detalle de Impuestos',
        readonly=True,
    )

    tax_client_ids = fields.One2many(
        'account.retention.client.tax',
        'retention_id',
        'Impuestos',
        #readonly=True,
        #states={'draft': [('readonly', False)]},

    )
    move_client_id = fields.Many2one(
        'account.move',
        string='Asiento Contable',
        readonly=True,
        store=True
    )

    date = fields.Date(
        string='Date',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
        default=fields.Date.context_today
    )

    ref = fields.Char(string='Referecia', copy=False, tracking=True, states={'draft': [('readonly', False)]})
    narration = fields.Text(string=u'Descripción')
    state = fields.Selection(selection=[
        ('draft', 'Borrador'),
        ('posted', 'Publicado'),
        ('cancel', 'Cancelado'),
    ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')

    journal_id = fields.Many2one('account.journal', string='Diario', required=False, readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 check_company=True,)
    type = fields.Selection(
        [
            ('out_invoice', 'Factura de Venta'),
            ('in_invoice', 'Factura de Compra'),
            ('liq_purchase', u'Liquidación Compra')],
        string='Tipo Comprobante',
        readonly=True,
        required=True,
        states={'draft': [('readonly', False)]},
        default='liq_purchase'
    )

    invoice_id = fields.Many2one(
        'account.move',
        string='Documento',
        required=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain=[('state', '!=', 'draft'),('move_type','in',['out_invoice','in_invoice'])]
    )

    partner_id = fields.Many2one(
        related='invoice_id.partner_id',
        string='Empresa',
        store=True
    )

    amount_total = fields.Float(
        compute='_amount_total',
        string='Total',
        store=True
    )

    @api.depends('tax_ids.balance')
    def _amount_total(self):
        # self.ensure_one()
        for rec in self:
            if rec.move_type not in ['ret_out_invoice']:
                amount_total = 0
                for tax in rec.tax_ids:
                    amount_total += round(tax.balance, 2)

                rec.amount_total = abs(amount_total)
            else:
                amount_total = 0
                for taxc in rec.tax_client_ids:
                    amount_total += round(taxc.amount_total, 2)
                rec.amount_total = abs(amount_total)
                # rec.amount_total =abs(sum( round(taxc.amount_total,2) for taxc in rec.tax_client_ids))



    def action_retention_cancel(self):
        for inv in self:
            if inv.retention_id:
                inv.retention_id.action_cancel()
        return True

    def button_validate(self):
        """
        Botón de validación de Retención que se usa cuando
        se creó una retención manual, esta se relacionará
        con la factura seleccionada.
        """

        for ret in self:

            if not ret.partner_id.vat or not self.partner_id.l10n_latam_identification_type_id:
                if ret.type == 'ret_out_invoice':
                    raise ValidationError(u"Los datos del cliente no estan correctamente configurados.")
                else:
                    raise ValidationError(u"Los datos del proveedor no estan correctamente configurados.")

            if ret.journal_id.type == 'purchase' and not ret.journal_id.retention_sequence_id:
                raise ValidationError(u"No se ha establecido una secuencia de retenciones para el diario de compras [%s]."% ret.journal_id.name)

            invoice = self.env['account.move'].browse(ret.invoice_id.id)
            if invoice.retention_id:
                raise ValidationError(
                    _(u'La factura a la que se desea realizar la retención ya contiene un documento de este tipo.'))
            #elif ret.manual:
            #    ret.action_validate(ret.name)
            #    invoice.write({'retention_id': ret.id})
            else:
                ret.action_validate(ret.name)
        return True

    def action_validate(self, number=None):
        """
        number: Número posible para usar en el documento

        Método que valida el documento, su principal
        accion es numerar el documento segun el parametro number
        """

        for wd in self:

            if wd.move_type not in ['ret_out_invoice']:

                sequence = wd.journal_id.retention_sequence_id

                if wd.name and wd.name != '/' and not number:
                    wd_number = wd.name
                elif not number:
                    number = sequence.next_by_id()

                else:
                    number = str(number).zfill(sequence.padding)

                if not number:
                    raise ValidationError(
                        u"Verifique que el diario usado tenga la configurado la autorización de retenciones y/o la misma sea valida.")


                wd.write({'state': 'posted', 'name': number})

            else:

                if number and len(str(number)) == 15:
                    wd.write({'state': 'posted', 'name': number})
                elif wd.name and len(str(wd.name)) == 15:
                    wd.write({'state': 'posted', 'name': wd.name})
                else:
                    raise ValidationError(_(u'El número de retención es incorrecto o no ha sido introducido.'))

                    # Create one move line per voucher line where amount is not 0.0

        return True

    def action_cancel(self):
        """
        Método para cambiar de estado a cancelado el documento
        """
        auth_obj = False
        for ret in self:
            data = {'state': 'cancel'}
            if ret.move_type == 'ret_in_invoice' and ret.invoice_id.state == 'posted':
                raise ValidationError(
                    _(u'No se permiten anular retenciones con facturas publicados. Por favor anule antes la factura correspondiente.'))
            elif ret.move_type == 'ret_out_invoice':
                if ret.move_client_id:
                    move = self.env['account.move'].browse(ret.move_client_id.id)
                    if move:
                        if move.state == 'posted':
                            raise ValidationError(
                                _(u'No se permiten anular retenciones con asientos contables publicados. Por favor anule antes el asiento contable correspondiente.'))
                        else:
                            move.unlink()

            self.write({'state': 'cancel'})

            invoice = self.env['account.move'].browse(ret.invoice_id.id)
            invoice.write({'retention_id': False})

        return True

    def action_draft(self):
        for obj in self:
            self.write({'state': 'draft'})
        return True

    def action_move_client_create(self):
        """ Creates retention related analytics and financial move lines """
        account_move = self.env['account.move']
        account_invoice = self.env['account.move']
        for ret in self:
            inv = account_invoice.browse(ret.invoice_id.id)

            if not ret.tax_client_ids:
                raise Warning(_(u'Cree algunas líneas en la retencion'))
            if ret.move_client_id and ret.move_client_id.state != 'draft':
                raise Warning(_(u'La retención ya posee un asiento contable asentado.'))
            if ret.move_type not in ('ret_out_invoice'):
                raise Warning(_(u'Solo se pueden generar asientos para retenciones de clientes.'))
            if inv.state not in ('posted'):
                raise Warning(
                    _(u'La factura a la que se desea generar la retención no se encuentra validada o ya ha sido pagada en su totalidad.'))
            if inv.retention_id and inv.retention_id != self.id:
                raise Warning(
                    _(u'La factura a la que se desea generar la retención ya contiene otra retención asociada.'))

            ctx = dict(self._context, lang=ret.partner_id.lang)
            date_invoice = ret.date

            #if ret.type in ('ret_out_invoice'):
            #    ref = u"Retención #" + ret.name

            name = ret.name or '/'
            ref = u"Retención #" + name
            journal = inv.journal_id.with_context(ctx)

            line = [(0, 0, {
                'name': name,
                'credit': round(ret.amount_total, 2),
                'account_id': ret.partner_id.property_account_receivable_id.id,
                'ref': ref,
                'partner_id': ret.partner_id.id
            })]

            for tax_line in ret.tax_client_ids:
                invoice_repartition = tax_line.tax_id.invoice_repartition_line_ids.filtered(lambda a: a.account_id.id != False)
                if len(invoice_repartition) == 0:
                    raise UserError("Debe configurar la cuenta contable asociada al impuesto %s" % tax_line.tax_id.name)

                line += [(0, 0, {
                    'name': tax_line.tax_id.name,
                    'debit': round(tax_line.amount_total, 2),
                    'account_id': invoice_repartition[0].account_id.id,
                    'ref': ref,
                    'partner_id': ret.partner_id.id,
                })]

            _type = self.env['l10n_latam.document.type'].search(
                [('l10n_ec_type', '=', 'out_withhold')], limit=1)
            if len(_type) == 0:
                raise ValidationError(
                    u"No existe un tipo de documento que permita realizar las retenciones de clientes.")

            move_vals = {
                'ref': ref + ' #'+name,
                'line_ids': line,
                #'partner_id': ret.partner_id.id,
                #'journal_id': journal.id,
                'date': date_invoice,
                'narration': "",
                'move_type': 'entry',
                'l10n_latam_document_type_id': _type[0].id
            }

            if ret.move_client_id:
                move = ret.move_client_id
                move.line_id.unlink()
                move.write(move_vals)
            else:
                move = account_move.with_context(ctx).create(move_vals)

            vals = {
                'move_client_id': move.id,
                'state': 'posted'
            }

            ret.with_context(ctx).write(vals)


            inv.write({'retention_id': ret.id})

            move.action_post()
            # reconcilie partial retention with invoice
            move_line_pool = self.pool.get('account.move.line')
            prepare_line = []
            # lieneas de la factura
            line_1 = inv.line_ids.filtered(lambda line: line.debit > 0 and line.account_id.user_type_id.type in ['receivable','payable'])
            # lieneas de la retencion
            line_2 = move.line_ids.filtered(lambda line: line.credit > 0 and line.account_id.user_type_id.type in ['receivable','payable'])

            res = (line_1 + line_2).reconcile()

        return True

    def unlink(self):
        for obj in self:
            if obj.state in ['done']:
                raise Warning(_('No se permite borrar retenciones validadas.'))

            if obj.move_client_id:
                move = self.env['account.move'].browse(obj.move_client_id.id)
                if move:
                    move.unlink()
            invoice = self.env['account.move'].browse(obj.invoice_id.id)
            if invoice:
                invoice.write({'retention_id': False})
        res = super(AccountRetention, self).unlink()
        return res