# -*- coding: utf-8 -*-
__author__ = 'yordany'
import logging
import time
from datetime import date
from odoo import models
from odoo import api, fields, models, _

class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    l10n_ec_type = fields.Selection(related='tax_group_id.l10n_ec_type', store=True, index=True)
    l10n_ec_tax_base = fields.Float(compute='compute_l10n_latam_tax_base_retention')
    retention_id = fields.Many2one('account.retention', string='Retención de Impuestos', copy=False)

    fiscal_year = fields.Integer(
        string=u'Año fiscal',
        required=False, compute='compute_retention_values')

    abs_tax_amount = fields.Float(
        string='Monto',
        required=False, compute='compute_retention_values')

    abs_percent = fields.Float(
        string=' Porcentaje',
        required=False, compute='compute_retention_values')

    @api.depends('price_subtotal')
    def compute_retention_values(self):
        abs_tax_amount = 0
        abs_percent = 0
        fiscal_year = int(time.strftime("%Y"))
        for line in self:
            line.abs_tax_amount = abs(line.balance)
            line.fiscal_year = line.date.year
            line.abs_percent = abs(line.tax_line_id.amount)


    @api.depends('price_unit', 'price_subtotal')
    def compute_l10n_latam_tax_base_retention(self):
        tax_calculate = {}
        for line in self:
            base_tax = 0.00
            invoice = line.move_id
            if line.l10n_ec_type in ['withhold_income_tax']:
                base_tax = invoice.amount_untaxed

            if line.l10n_ec_type in ['withhold_vat']:
                if not invoice.id in tax_calculate:
                    base_tax = sum(abs(inv.balance) for inv in
                                   invoice.line_ids.filtered(lambda a: a.l10n_ec_type in ['vat12', 'vat14']))
                    tax_calculate[invoice.id] = base_tax
                else:
                    base_tax = tax_calculate[invoice.id]


            line.l10n_ec_tax_base = base_tax

