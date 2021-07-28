from odoo import fields, models, api
import time

class AccountWithdrawingClientTax(models.Model):
    _name = 'account.retention.client.tax'
    _rec_name = 'name'
    _description = u'Impuestos de retención de cliente'

    fiscal_year = fields.Char('Ejercicio Fiscal', size=4, store=True, compute='_compute_fiscal_year')
    percent = fields.Float('Porcentaje', store=True, readonly=True,
                           compute='_compute_percent')
    retention_id = fields.Many2one('account.retention', 'Retención')
    amount_base = fields.Float(string='Base', store=True, readonly=False)
    tax_id = fields.Many2one('account.tax', "Código Impuesto", required=True, )
    name = fields.Char(u'Descripción', size=60, store=True, readonly=True, compute='_compute_description')
    amount_total = fields.Float(string='Total', store=True, compute='_compute_amount', readonly=True)

    @api.depends('amount_base', 'tax_id')
    def _compute_amount(self):
        for rec in self:
            if rec.tax_id:
                rec.amount_total = round(rec.amount_base * (abs(float(rec.tax_id.amount)) / 100), 2)

    @api.depends('retention_id', 'retention_id.date')
    def _compute_fiscal_year(self):
        for rec in self:
            if rec.retention_id.date:
                year = rec.retention_id.date.year
                rec.fiscal_year = year

    @api.depends('tax_id')
    def _compute_percent(self):
        result = {}
        for line in self:
            if line.tax_id:
                if line.tax_id.tax_group_id.l10n_ec_type in ['withhold_vat','withhold_income_tax']:
                    line.percent = abs(float(line.tax_id.amount))
                else:
                    line.percent = 0
            else:
                line.percent = 0

        return result

    @api.depends('tax_id')
    def _compute_description(self):
        result = {}
        for line in self:
            if line.tax_id:
                if line.tax_id.tax_group_id.l10n_ec_type in ['withhold_vat','withhold_income_tax']:
                    line.name = line.tax_id.name
                else:
                    line.name = ""
            else:
                line.name = ""

        return result

    @api.onchange('tax_id')
    def _compute_amount_base(self):
        tax_calculate = {}
        for line in self:
            invoice = line.retention_id.invoice_id
            if not invoice:
                raise Warning("Debe seleccionar un documento")
            if line.tax_id:
                if line.tax_id.tax_group_id.l10n_ec_type in ['withhold_income_tax']:
                    line.amount_base = invoice.amount_untaxed
                elif line.tax_id.tax_group_id.l10n_ec_type in ['withhold_vat']:
                    if not invoice.id in tax_calculate:
                        base_tax = sum(abs(inv.balance) for inv in
                                       invoice.line_ids.filtered(
                                           lambda a: a.l10n_ec_type in ['vat12', 'vat14']))
                        tax_calculate[invoice.id] = base_tax
                        line.amount_base = base_tax
                    else:
                        base_tax = tax_calculate[invoice.id]
                        line.amount_base = base_tax
                else:
                    line.amount_base = 0 #invoice.amount_tax  # - invoice.amount_ice
            else:
                line.amount_base = 0

    _defaults = {
        'fiscal_year': time.strftime('%Y'),
        'company_id': lambda self: self.env.user.company_id
    }