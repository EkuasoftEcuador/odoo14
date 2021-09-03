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
from odoo import api, fields, models, _

class ek_incoterms_terms(models.Model):


    _name = 'ek.incoterms.terms'
    _description = u'Rubros de Incoterms'
    _order = 'sequence'

    name = fields.Char('Rubro', required=True, readonly=False)
    code = fields.Char(u'Código', size=64, required=True, readonly=False)
    sequence = fields.Integer('Orden', default=1, required=True, help=u'Úselo para organizar la secuencia de cálculo',
                              select=True)
    note = fields.Text(u'Descripción')
    type = fields.Selection(string="Tipo", default='other', selection=[('freight', 'Flete'),('insurance', 'Seguro'),('expense', 'Gasto'), ('calculate', u'Calculo de Aduanero'), ('other', 'Otros'), ('liquidation', 'Otros'), ], required=True, )
    is_considered_total = fields.Boolean(default=True, string="Considerado en el total?",  help=u"Indica que este rubro sera considerado en el total de la importación")
    is_provider_assumed = fields.Boolean(string="Valor asumido por el proveedor?",  help=u"Si esta casilla está marcada este solo sera usado para el calculo de los tributos")

class stock_incoterms_terms(models.Model):


    _name = 'ek.stock.incoterms.terms'
    _description = u'Terminos de Incoterms'
    _order = 'sequence'

    terms_id = fields.Many2one("ek.incoterms.terms", string="Termino", required=True)
    code = fields.Char(u'Código', size=64, required=False, readonly=False, related="terms_id.code", store=True)
    type = fields.Selection(string="Tipo",
                            selection=[('freight', 'Flete'), ('insurance', 'Seguro'), ('expense', 'Gastos'),
                                       ('other', 'Otros'), ], required=False, store=True, related="terms_id.type")
    sequence = fields.Integer('Orden', default=1, required=True, help=u'Úselo para organizar la secuencia de cálculo',
                              select=True,related="terms_id.sequence", store=True)
    is_required = fields.Boolean(string="Requerido?",  default=False, help="Indica que el rubro debe ser requerido.")

    incoterm_id = fields.Many2one("account.incoterms", string="Incoterm", required=False)

#stock.incoterms
class stock_incoterms(models.Model):

    _inherit = 'account.incoterms'
    incoterms_terms_ids = fields.One2many("ek.stock.incoterms.terms", inverse_name="incoterm_id", string="Rubos", required=False)
