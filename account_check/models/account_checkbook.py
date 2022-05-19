##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
##############################################################################
#    Sistema FINAMSYS
#    2021-Manteiner Today Ekuasoft S.A
#
#    Collaborators of this module:
#    Coded by: Cristhian Luzon <@cristhian_70>
#    Planifyied by: Yordany Oliva
#
##############################################################################
from odoo import fields, models, api, _
import logging
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)


class AccountCheckbook(models.Model):

    _name = 'account.checkbook'
    _description = 'Account Checkbook'

    name = fields.Char(
        compute='_compute_name',
    )
    sequence_id = fields.Many2one(
        'ir.sequence',
        'Secuencia',
        copy=False,
        domain=[('code', '=', 'issue_check')],
        help="Checks numbering sequence.",
        context={'default_code': 'issue_check'},
    )
    next_number = fields.Integer(
        'Siguiente Número',
        # usamos compute y no related para poder usar sudo cuando se setea
        # secuencia sin necesidad de dar permiso en ir.sequence
        compute='_compute_next_number',
        inverse='_inverse_next_number',
    )
    issue_check_subtype = fields.Selection(
        [('deferred', 'Diferidos'), ('currents', 'Corrientes')],
        string='Tipo de Chequera',
        required=True,
        default='deferred',
        help='* Con cheques corrientes el asiento generado por el pago '
        'descontará directamente de la cuenta de banco y además la fecha de '
        'pago no es obligatoria.\n'
        '* Con cheques diferidos el asiento generado por el pago se hará '
        'contra la cuenta definida para tal fin en la compañía, luego será '
        'necesario el asiento de débito que se puede generar desde el extracto'
        ' o desde el cheque.',
    )
    journal_id = fields.Many2one(
        'account.journal', 'Diario',
        help='Journal where it is going to be used',
        readonly=True,
        required=True,
        domain=[('type', '=', 'bank')],
        ondelete='cascade',
        context={'default_type': 'bank'},
        states={'draft': [('readonly', False)]},
        auto_join=True,
    )
    debit_journal_id = fields.Many2one(
        'account.journal', 'Diario de Debito del Cheque Propio',
        help='Diario del cual se realizara el debito del cheque ',
        readonly=True,
        required=False,
        domain=[('type', '=', 'bank')],
        context={'default_type': 'bank'},
        states={'draft': [('readonly', False)]})
    bank_id = fields.Many2one(
        'res.bank', 'Banco',
        required=False,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    range_to = fields.Integer(
        'Ultimo Número',
        # readonly=True,
        # states={'draft': [('readonly', False)]},
        help='Si establece un número aquí, esta chequera será automáticamente'
        'utilizada hasta alcanzar este número.'
    )
    issue_check_ids = fields.One2many(
        'account.check',
        'checkbook_id',
        string='Cheques Propios',
        readonly=True,
    )
    state = fields.Selection(
        [('draft', 'Borrador'), ('active', 'En uso'), ('used', 'Usado')],
        string='Estado',
        # readonly=True,
        default='draft',
        copy=False,
    )
    # TODO depreciar esta funcionalidad que no estamos usando
    block_manual_number = fields.Boolean(
        default=True,
        string='Bloquear Número Manual?',
        # readonly=True,
        # states={'draft': [('readonly', False)]},
        help='Block user to enter manually another number than the suggested'
    )
    numerate_on_printing = fields.Boolean(
        default=False,
        string='Numerar en impresion?',
        # readonly=True,
        # states={'draft': [('readonly', False)]},
        help='No se asignará ningún número al crear el pago, el número se asignará después de imprimir el cheque.'
    )
    report_template = fields.Many2one(
        'ir.actions.report',
        'Report',
        domain="[('model', '=', 'account.payment')]",
        context="{'default_model': 'account.payment'}",
        help='Report to use when printing checks. If not report selected, '
        'report with name "check_report" will be used',
    )
    content = fields.Html(string="Plantilla")

    @api.depends('sequence_id.number_next_actual')
    def _compute_next_number(self):
        for rec in self:
            rec.next_number = rec.sequence_id.number_next_actual

    def _inverse_next_number(self):
        for rec in self.filtered('sequence_id'):
            rec.sequence_id.sudo().number_next_actual = rec.next_number

    @api.model
    def create(self, vals):
        rec = super(AccountCheckbook, self).create(vals)
        if not rec.sequence_id:
            rec._create_sequence(vals.get('next_number', 0))
        return rec

    def _create_sequence(self, next_number):
        """ Create a check sequence for the checkbook """
        for rec in self:
            rec.sequence_id = rec.env['ir.sequence'].sudo().create({
                'name': '%s - %s' % (rec.journal_id.name, rec.name),
                'implementation': 'no_gap',
                'padding': 8,
                'number_increment': 1,
                'code': 'issue_check',
                # si no lo pasamos, en la creacion se setea 1
                'number_next_actual': next_number,
                'company_id': rec.journal_id.company_id.id,
            })

    def _compute_name(self):
        for rec in self:
            if rec.issue_check_subtype == 'deferred':
                name = _('Cheques Diferidos')
            else:
                name = _('Cheques Corrientes')
            if rec.range_to:
                name += _(' up to %s') % rec.range_to
            rec.name = name

    def unlink(self):
        if self.mapped('issue_check_ids'):
            raise ValidationError(
                _('You can drop a checkbook if it has been used on checks!'))
        return super(AccountCheckbook, self).unlink()
