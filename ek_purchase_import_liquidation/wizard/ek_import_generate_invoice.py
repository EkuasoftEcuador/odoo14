# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ek_import_generate_invoice(models.TransientModel):
    """Asociar regalias a viaje"""
    _name = 'ek.import.generate.invoice'
    _description = _(u'Generar Facturas desde Ordenes de Importación')

    is_gruping = fields.Boolean(string="Agrupar Facturas?",  default=True)
    name = fields.Char(u"Número")
    date = fields.Date(string="Fecha", required=False, )
    reference = fields.Char(string="Referencia", required=False, )
    partner_id = fields.Many2one('res.partner', u'Proveedor', required=False)
    note = fields.Text(string="Notas", required=False, )
    import_liquidation_id = fields.Many2one(comodel_name="ek.import.liquidation", string=u"Importación",
                                            required=False, )
    journal_id = fields.Many2one(comodel_name="account.journal", string="Diario", required=False, )

    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', 'Tipo de Documento')

    def action_confirm(self):

        active_ids = self.env.context.get('active_ids')
        obtects = self.env['ek.import.liquidation'].browse(active_ids).filtered(lambda x: x.state in ['draft', 'calculate'])
        obj_invoice = self.env['account.move']
        data_invoice = {}

        for rec in obtects:
            #
            date_due = fields.Date.context_today(self)
            pterm = self.env['account.payment.term'].browse(rec.partner_id.property_supplier_payment_term_id and rec.partner_id.property_supplier_payment_term_id.id or 0)
            if pterm:
                pterm_list = pterm.compute(value=1, date_ref=self.date)[0]
                if pterm_list:
                    date_due=max(line[0] for line in pterm_list)

            for line in rec.order_line.filtered(lambda x: not x.invoice_id):

                partner = line.purchase_line_id.order_id.partner_id or rec.partner_id

                account_id = line.product_id.property_account_expense_id and line.product_id.property_account_expense_id.id or False
                if not account_id:
                    account_id = line.product_id.categ_id and line.product_id.categ_id.property_account_expense_categ_id.id or False

                _line = {
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'account_id': account_id,
                    'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                    'quantity': line.product_qty,
                    'price_unit': line.price_unit,
                    'tax_ids':[],
                    'price_subtotal': line.price_subtotal,
                    'liquidation_line_id': line.id
                }

                if self.is_gruping:
                    key = "PAR-%s" % (partner.id)
                else:
                    key = "OC-%s" % (line.purchase_line_id.order_id.name)

                if key not in data_invoice:
                    data_invoice[key] = {
                        'partner_id':   partner.id,
                        'invoice_payment_term_id':rec.partner_id.property_supplier_payment_term_id and rec.partner_id.property_supplier_payment_term_id.id or None,
                        'invoice_date': self.date,
                        'invoice_date_due': date_due,
                        'state':        'draft',
                        'posted_before':   False,
                        'move_type': 'in_invoice',
                        'ref':         self.reference,
                        'narration':       self.note,
                        'invoice_liquidation_id': rec.id,
                        'journal_id': self.journal_id.id,
                        'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
                        'l10n_latam_document_number': self.name,
                        'invoice_line_ids': []
                    }


                data_invoice[key]['invoice_line_ids'].append( (0,0, _line))

            invoice_created = []

            if len(data_invoice) > 0:
                for key, data in data_invoice.items():

                    inv = obj_invoice.create(data)
                    for line in inv.invoice_line_ids:
                        line.liquidation_line_id.write({'invoice_id': inv.id})

                    invoice_created.append(inv.id)
            else:
                #CREAR FACTURA VACIA
                inv = obj_invoice.create({
                    'partner_id':   partner.id,
                    'invoice_payment_term_id':rec.partner_id.property_supplier_payment_term_id and rec.partner_id.property_supplier_payment_term_id.id or None,
                    'invoice_date': self.date,
                    'invoice_date_due': date_due,
                    'state':        'draft',
                    'move_type': 'in_invoice',
                    'ref':         self.reference,
                    'narration':       self.note,
                    'invoice_liquidation_id': rec.id,
                    'journal_id': self.journal_id.id,
                    'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
                    'l10n_latam_document_number': self.name,
                })
                invoice_created.append(inv.id)

            if len(invoice_created) > 0:
                if len(rec.invoice_ids.ids) > 0:
                    invoice_created.extend(rec.invoice_ids.ids)
                rec.write({'invoice_ids': [(6,0,invoice_created)]})