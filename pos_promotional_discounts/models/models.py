# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################
from odoo import fields, models, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    wk_promo_messages = fields.Many2many('pos.promotions', string='Promo Messages', domain=[('criteria_type','=','specific_items')])

class PosCategory(models.Model):
    _inherit = 'pos.category'

    wk_promo_messages = fields.Many2many('pos.promotions', string='Promo Messages', domain=[('criteria_type','=','specific_categ')])

class PosConfig(models.Model):
	_inherit = 'pos.config'

	promo_message_ids = fields.Many2many('pos.promotions',string="Promotions")
	show_apply_promotion = fields.Boolean(string="Show Apply Promotion Button", help="Enable this option to Show Promotions button on POS, or the offers will be applied automatically.", default=False)
	show_offers_in_orderline = fields.Boolean(string="Show Offers in Orderlines", help="Enable this option to Show Offers in Orderline.", default=True)

class PosSession(models.Model):
	_inherit = 'pos.session'

	def _wk_customer_and_order_cont(self):
		for pos_obj in self:
			pos_obj.customer_count =  pos_obj.env['pos.order'].search_count([('partner_id','!=',False),('session_id','=',pos_obj.id)])
			pos_obj.order_count =  pos_obj.env['pos.order'].search_count([('session_id','=',pos_obj.id)]) +1

	customer_count = fields.Integer(compute="_wk_customer_and_order_cont", string='Customer Count')
	order_count = fields.Integer(compute="_wk_customer_and_order_cont", string="Order Count")