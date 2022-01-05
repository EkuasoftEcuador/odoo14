# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from stdnum.ec import ci, ruc
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def check_vat_ec(self, vat):
        for rec in self:
            if rec.l10n_latam_identification_type_id.is_vat:
                ruc_vat_type = self.env.ref('ek_l10n_ec.ec_ruc')
                ced_vat_type = self.env.ref('ek_l10n_ec.ec_dni')
                if rec.l10n_latam_identification_type_id in (ruc_vat_type, ced_vat_type):
                    # temporal fix as stdnum.ec is allowing old format with a dash in between the number
                    if not rec.vat.isnumeric():
                        raise ValidationError(_('Ecuadorian VAT number must contain only numeric characters'))
                if rec.l10n_latam_identification_type_id == ced_vat_type:
                    return ci.is_valid(vat)
                elif rec.l10n_latam_identification_type_id == ruc_vat_type and vat != '9999999999999':
                    return ruc.is_valid(vat)
        return True

    def _get_complete_address(self):
        self.ensure_one()
        partner_id = self
        address = ""
        if partner_id.street:
            address += partner_id.street + ", "
        if partner_id.street2:
            address += partner_id.street2 + ", "
        if partner_id.city:
            address += partner_id.city + ", "
        if partner_id.state_id:
            address += partner_id.state_id.name + ", "
        if partner_id.zip:
            address += "(" + partner_id.zip + ") "
        if partner_id.country_id:
            address += partner_id.country_id.name
        return address

    @api.constrains('vat','l10n_latam_identification_type_id','company_id')
    def _check_exist_parnter(self):
        for record in self:
            exits = 0
            if record.vat and record.vat != '':
                exits = self.search_count([('l10n_latam_identification_type_id', '=', record.l10n_latam_identification_type_id.id),('vat','=',record.vat),('company_id','=',record.company_id.id)])

            if exits > 1:
                raise ValidationError("Los clientes/proveedores deben ser únicos.")