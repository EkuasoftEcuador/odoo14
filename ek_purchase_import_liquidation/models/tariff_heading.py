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
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval as eval

class ek_tariff_rule_category(models.Model):


    _name = 'ek.tariff.rule.category'
    _description = u'Categoría de regla arancelaria'

    name = fields.Char('Nombre', required=True, readonly=False)
    code = fields.Char(u'Código', size=64, required=True, readonly=False)
    parent_id = fields.Many2one('ek.tariff.rule.category', 'Padre', help=u"La vinculación de una categoría de tarifa a su principal se usa solo para el propósito de informar.")
    children_ids = fields.One2many('ek.tariff.rule.category', 'parent_id', 'Hijos')
    note = fields.Text(u'Descripción')



class ek_tariff_rule(models.Model):

    _name = 'ek.tariff.rule'
    _description = u'Reglas de Trifas Arancelarias'
    _order = 'sequence'
    name = fields.Char('Nombre', required=True, readonly=False)
    code = fields.Char(u'Código', size=64, required=True, help=u"El código de las reglas de tarifas se puede usar como referencia en el cálculo de otras reglas. En ese caso, es sensible a mayúsculas y minúsculas.")
    sequence = fields.Integer('Secuencia', required=True, help=u'Úselo para organizar la secuencia de cálculo', select=True)
    quantity = fields.Char('Cantidad', help=u"Se usa en el cálculo por porcentaje y cantidad fija.")
    category_id = fields.Many2one('ek.tariff.rule.category', u'Categoría', required=True)
    active = fields.Boolean('Activo', help=u"Si el campo activo está configurado en falso, le permitirá ocultar la regla de tarifa sin eliminarla.")
    condition_select = fields.Selection([('none', 'Siempre Verdadero'),('range', 'Intervalo'), ('python', u'Expresión de Python')], u"Condición basada en", required=True)
    condition_range = fields.Char('Intervalo basado en', readonly=False, help=u'Esto se usará para calcular los valores de% de los campos; en general es básico, pero también puede usar campos de códigos de categorías en minúsculas como nombres de variables (hra, ma, lta, etc.) y la variable básica.')
    condition_python = fields.Text(u'Condición python', required=True, readonly=False, help=u'Aplica esta regla para el cálculo si la condición es verdadera. Puede especificar condiciones como basic> 1000.')
    condition_range_min = fields.Float(u'Intervalo mínimo', required=False, help=u"El monto mínimo, aplicado para esta regla.")
    condition_range_max = fields.Float(u'Intervalo máximo', required=False, help=u"La cantidad máxima, aplicada para esta regla.")
    amount_select  = fields.Selection([
        ('percentage','Porcentaje (%)'),
        ('fix','Importe Fijo'),
        ('code',u'Código Python')
    ],'Tipo de importe', select=True, required=True, help=u"El método de cálculo para la cantidad de regla.")
    amount_fix = fields.Float('Importe fijo', digits_compute='Payroll',)
    amount_percentage = fields.Float('Porcentaje (%)', digits_compute='Payroll Rate', help=u'Por ejemplo, ingrese 50.0 para aplicar un porcentaje del 50%')
    amount_python_compute = fields.Text(u'Código python')
    amount_percentage_base = fields.Char('Porcentaje basado en', required=False, readonly=False, help=u'El resultado se verá afectado por una variable')
    note = fields.Text(u'Descripción')
    param = fields.Boolean(string=u"Parámento",  help=u"Indica que esta regla sera usada para el calculo de las demas y no se tendra en cuenta en la suma del total")
    terms_id = fields.Many2one(comodel_name="ek.incoterms.terms", string="Aplicar A", required=False)

    _defaults = {
        'amount_python_compute': '''
# Available variables:
#----------------------
# payslip: object containing the payslips
# employee: hr.employee object
# contract: hr.contract object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
# worked_days: object containing the computed worked days.
# inputs: object containing the computed inputs.

# Note: returned value have to be set in the variable 'result'

result = contract.wage * 0.10''',
        'condition_python':
'''
# Available variables:
#----------------------
# payslip: object containing the payslips
# employee: hr.employee object
# contract: hr.contract object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
# worked_days: object containing the computed worked days
# inputs: object containing the computed inputs

# Note: returned value have to be set in the variable 'result'

result = rules.NET > categories.NET * 0.10''',
        'condition_range': 'contract.wage',
        'sequence': 5,
        'appears_on_payslip': True,
        'active': True,
        'condition_select': 'none',
        'amount_select': 'fix',
        'amount_fix': 0.0,
        'amount_percentage': 0.0,
        'quantity': '1.0',
     }

    @api.model
    def _recursive_search_of_rules(self, cr, uid, rule_ids, context=None):
        """
        @param rule_ids: list of browse record
        @return: returns a list of tuple (id, sequence) which are all the children of the passed rule_ids
        """
        children_rules = []
        for rule in rule_ids:
            if rule.child_ids:
                children_rules += self._recursive_search_of_rules(cr, uid, rule.child_ids, context=context)
        return [(r.id, r.sequence) for r in rule_ids] + children_rules

    #TODO should add some checks on the type of result (should be Float)
    def compute_rule(self,localdict):
        """
        :param rule_id: id of rule to compute
        :param localdict: dictionary containing the environement in which to compute the rule
        :return: returns a tuple build as the base/amount computed, the quantity and the rate
        :rtype: (Float, Float, Float)
        """
        rule = self
        if rule.amount_select == 'fix':
            try:
                return rule.amount_fix, float(eval(rule.quantity, localdict)), 100.0
            except:
                raise UserError( _('Cantidad incorrecta definida para la regla de tarifa %s (%s).')% (rule.name, rule.code))
        elif rule.amount_select == 'percentage':
            try:
                return (float(eval(rule.amount_percentage_base, localdict)),
                        float(eval(rule.quantity, localdict)),
                        rule.amount_percentage)
            except:
                raise UserError( _('Porcentaje incorrecto de base o cantidad definida para la regla %s (%s).')% (rule.name, rule.code))
        else:
            try:
                eval(rule.amount_python_compute, localdict, mode='exec', nocopy=True)
                return float(localdict['result']), 'result_qty' in localdict and localdict['result_qty'] or 1.0, 'result_rate' in localdict and localdict['result_rate'] or 100.0
            except:
                raise UserError( _('Código python incorrecto definido para la regla %s (%s).')% (rule.name, rule.code))

    def satisfy_condition(self, localdict):
        """
        @param rule_id: id of hr.salary.rule to be tested
        @param contract_id: id of hr.contract to be tested
        @return: returns True if the given rule match the condition for the given contract. Return False otherwise.
        """

        if self.condition_select == 'none':
            return True
        elif self.condition_select == 'range':
            try:
                result = eval(self.condition_range, localdict)
                return self.condition_range_min <=  result and result <= self.condition_range_max or False
            except:
                raise UserError( _('Condición de rango incorrecto definida para la regla %s (%s).')% (self.name, self.code))
        else: #python code
            try:
                eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return 'result' in localdict and localdict['result'] or False
            except:
                raise UserError( _('Código python incorrecto definido para la regla %s (%s).')% (self.name, self.code))


class ek_tariff_heading(models.Model):
    _name = "ek.tariff.heading"
    _description = 'Partida Arancelaria'

    type = fields.Selection(string=u"Tipo", selection=[('view', 'Vista'), ('regular', 'Regular'), ], required=True, default='regular')
    code = fields.Char(string=u"Código", required=True, help="",)
    name = fields.Char(string=u"Descripción Arancelaria", required=True, help="")
    note = fields.Text(string=u"Observación", required=False, help="")
    parent_id = fields.Many2one('ek.tariff.heading', 'Nivel Superior', ondelete='cascade', domain=[('type', '=', 'view')])
    child_parent_ids = fields.One2many('ek.tariff.heading', 'parent_id', 'Niveles Inferiores')
    active = fields.Boolean('Activo', select=2, default=True,
                             help=u"Si el campo activo está establecido en False, le permitirá ocultar la partida sin eliminarla.")
    parent_left = fields.Integer('Parent Left', select=1)
    parent_right = fields.Integer('Parent Right', select=1)
    tariff_rule_ids = fields.Many2many(comodel_name="ek.tariff.rule", relation="ek_tariff_heading_rule_rel", column1="tariff_id", column2="rule_id", string="Reglas", help="")
    tariff = fields.Float(string="Salvaguardia (%)", required=False, help="")
    tariff_percent = fields.Float(string="Arancel (En %)", required=False, digits='Importation Factor',)
    tariff_amount = fields.Float(string="Arancel Fijo", required=False, digits='Importation Factor',)
    unit_control = fields.Float(string="Unidad de Control", required=False, help="Unidad de control para trasa arancelaria")

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            args = domain + args
        srch_heading = self.search(args, limit=limit)
        return srch_heading and srch_heading.name_get() or []


    def _get_child_ids(self, cr, uid, ids, field_name, arg, context = None):
        result = {}
        for record in self.browse(cr, uid, ids, context=context):
            if record.child_parent_ids:
                result[record.id] = [x.id for x in record.child_parent_ids]
            else:
                result[record.id] = []

        return result

    def _check_recursion(self, cr, uid, ids, context = None):
        obj_self = self.browse(cr, uid, ids[0], context=context)
        p_id = obj_self.parent_id and obj_self.parent_id.id
        if (obj_self in obj_self.child_parent_ids) or (p_id and (p_id is obj_self.id)):
            return False
        return True



    _constraints = [
        (_check_recursion, 'Error!\nNo puede crear partidas recursivas.', ['parent_id'])
    ]
    _sql_constraints = [
        ('code_heading_uniq', 'unique(code)', u'El código de la partida debe ser único!')
    ]


    def name_get(self):
        if not self._ids:
            return []
        reads = self.browse(self._ids)
        res = []
        for record in reads:
            name = record.name
            if record.code:
                name = record.code
            res.append((record.id, name))

        return res
