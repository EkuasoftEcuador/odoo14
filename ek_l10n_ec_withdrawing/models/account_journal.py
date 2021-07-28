# -*- coding: utf-8 -*-
__author__ = 'yordany'
import logging
from datetime import date
from odoo import models
from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import time

class AccountJou(models.Model):
    _inherit = 'account.journal'

    retention_sequence_id = fields.Many2one('ir.sequence',
                                            string='Secuencia para retenciones',
                                            check_company=True, copy=False)



