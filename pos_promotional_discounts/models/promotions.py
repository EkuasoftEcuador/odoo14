# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_repr
import logging
_logger = logging.getLogger(__name__)

class PosPromotions(models.Model):
    _name = 'pos.promotions'
    _description = "Promotions"
    _order = "sequence asc, id desc"

    month_list = [('1','January'),
        ('2','February'),
        ('3','March'),
        ('4','April'),
        ('5','May'),
        ('6','June'),
        ('7','July'),
        ('8','August'),
        ('9','Septemper'),
        ('10','Octuber'),
        ('11','November'),
        ('12','December'),]

    name = fields.Char(string='Title', required=True)
    sequence = fields.Integer(default=10)
    criteria_type = fields.Selection([('every_new_customer','For Every New Customers '),
        ('every_x_order','For Every X Order Per POS Session '),
        ('first_x_customer','For First X Customers Per POS Session'),
        ('every_order','For Every Order '),('based_specific_date','Based On Specific Date'),
        ], string="Type of Criteria",required=True, default="every_order")
    
    offer_type = fields.Selection([('discount_on_products','Discount on Products'),    
                                    ('buy_x_get_y','Buy X Product & Get Y Product Free'),
                                    ('buy_x_get_y_qty', 'Buy X Product & Get Y Qty Product Free'),
                                    ('buy_x_get_discount_on_y', 'Buy X and Get Discount on Y Product'),
                                    ('get_x_discount_on_sale_total', 'Get X % Discount on Sale Total'),], required=True)
    discounted_ids = fields.One2many(comodel_name='discount.products', inverse_name='discount_product_id', string='Discounted Products')
    buy_x_get_y_ids = fields.One2many('buy_x.get_y', 'buy_x_get_y_id', string="Buy X Get Y")
    buy_x_get_y_qty_ids = fields.One2many('buy_x.get_y_qty', 'buy_x_get_y_qty_id', string="Buy X Get Y Qty")
    buy_x_get_discount_on_y_ids = fields.One2many('buy_x.get_discount_on_y', 'buy_x_get_discount_on_y_id', string="Buy X Get Discount on Y")
    discount_on_sale_total = fields.Integer("Discount on Sale Total")
    discount_product_id = fields.Many2one('product.product', string='Discount Product',
        domain="[('available_in_pos', '=', True), ('sale_ok', '=', True)]", help='The product used to model the discount.')
    discount_sale_total_ids =  fields.One2many('discount.sale.total', 'discount_sale_total_id', string="Discount Rules")

    active = fields.Boolean(string="Active", default=1)
    pos_ids = fields.Many2many('pos.config',string="Point Of Sale")
    product_tmplt_ids = fields.Many2many('product.template', string="Products", domain=[('available_in_pos','=',True)])
    no_of_customers = fields.Integer('Number of Customers')
    order_number = fields.Integer('Order Number (X)')
    wk_day = fields.Char(string="Day")
    wk_month = fields.Selection(month_list, default='1', string="Month")
    pos_categ_ids = fields.Many2many('pos.category' , string="POS Categories")

    @api.model
    def create(self, values):
        res = super(PosPromotions, self).create(values)
        promotions_objs = self.search([])
        ids = []
        if len(promotions_objs):
            for promotions_obj in promotions_objs:
                ids.append(promotions_obj.sequence)
        new_sequence = max(ids) + 1
        res.sequence = new_sequence
        return res

    @api.constrains('no_of_customers','order_number')
    def validate_customer_and_order_no(self):
        if (self.criteria_type == 'first_x_customer') and self.no_of_customers <= 0 :
            raise ValidationError("Number of customers must be greater than zero")
        if (self.criteria_type == 'every_x_order') and self.order_number <= 1 :
            raise ValidationError("Order number must be greater than one")

    @api.constrains('wk_day','wk_month', 'discount_sale_total_ids')
    def validate_day_mont(self):
        if(self.criteria_type == 'based_specific_date'):
            if not self.wk_month and not self.wk_day:
                raise ValidationError("Please enter the Day and Month")
            if not self.wk_month:
                raise ValidationError("Please enter the Month")
            elif not self.wk_day:
                raise ValidationError("Please enter the Day")

            if self.wk_month.isdigit() and self.wk_day.isdigit():
                wk_day =  int(self.wk_day)
                wk_month = int(self.wk_month)
                if wk_month >12 or wk_month <1:
                    raise ValidationError("Month can't be less than 0 or greater than 12")
                elif wk_month in [1,3,5,7,8,10,12]:
                    if (wk_day<1 or wk_day>31):
                        raise ValidationError("Please check the day in corresponding month")
                elif wk_month in [4,6,9,11]:
                    if (wk_day<1 or wk_day>30):
                        raise ValidationError("Please check the day in corresponding month")
                elif wk_month ==2 :
                    if (wk_day<1 or wk_day>28):
                        raise ValidationError("Please check the day in corresponding month")
            
            else:
                raise ValidationError("Day and month will be interger type")
        
        if(len(self.discount_sale_total_ids) > 1):
            for line1 in self.discount_sale_total_ids:
                for line2 in self.discount_sale_total_ids:
                    if(line1.id != line2.id):
                        flag = 0
                        if(line2.min_amount < line1.min_amount and line2.min_amount < line1.max_amount and line2.max_amount < line1.max_amount and line2.max_amount < line1.min_amount):
                            flag+=1
                        elif(line2.min_amount > line1.min_amount and line2.min_amount > line1.max_amount and line2.max_amount > line1.max_amount and line2.max_amount > line1.min_amount):
                            flag+=1
                        
                        if(not flag):
                            raise ValidationError('There is some overlapping in the Rule. Please Check and re-assign the Rules.')

class DiscountProducts(models.Model):
    _name = "discount.products"
    _order =  "apply_on, categ_id desc, id desc"

    def _get_default_currency_id(self):
        return self.env.company.currency_id.id

    discount_product_id = fields.Many2one('pos.promotions', string="Discounted Product")
    sequence = fields.Integer(default=16)
    currency_id = fields.Many2one('res.currency', string='Currency', default=_get_default_currency_id, required=True)
    apply_on = fields.Selection([
        ('3_all', 'All Products'),
        ('2_categories', 'Categories'),
        ('1_products', 'Products')],
        default='3_all', string='Apply On')
    categ_id = fields.Many2one('product.category', 'Product Category')
    product_id = fields.Many2one('product.product', 'Product Variant', domain=[('available_in_pos', '=', True)])
    name = fields.Char(string='Name', compute='_get_discount_line_name')
    percent_discount = fields.Float('Percentage Discount')
    discount = fields.Char('Discount', compute='_get_sale_discount_line_name_discount')

    @api.depends('apply_on', 'categ_id', 'product_id', 'percent_discount')
    def _get_discount_line_name(self):
        for item in self:
            if item.categ_id and item.apply_on == '2_categories':
                item.name = _("Category: %s") % (item.categ_id.display_name)
            elif item.product_id and item.apply_on == '1_products':
                item.name = _("Variant: %s") % (item.product_id.with_context(display_default_code=False).display_name)
            else:
                item.name = _("All Products")

    @api.depends('percent_discount','discount','currency_id')
    def _get_sale_discount_line_name_discount(self):
        for value in self:
            value.discount = _("%s %%") % (value.percent_discount)

class BuyXGetY(models.Model):
    _name = "buy_x.get_y"

    buy_x_get_y_id = fields.Many2one('pos.promotions', string="Buy X Get Y")
    product_x_id = fields.Many2one('product.product', domain=[('available_in_pos', '=', True)], string="Product X")
    qty_x = fields.Integer("Minimum Quantity")
    product_y_id =  fields.Many2one('product.product', domain=[('available_in_pos', '=', True)], string="Product Y")

    @api.constrains('qty_x')
    def check_constrains(self):
        for data in self:
            if(data.qty_x <= 0):
                raise ValidationError('Quantity of Product should be greater than 0')

class BuyXGetYQty(models.Model):
    _name = "buy_x.get_y_qty"

    buy_x_get_y_qty_id = fields.Many2one('pos.promotions', string="Buy X Get Y Qty")
    product_x_id = fields.Many2one('product.product', domain=[('available_in_pos', '=', True)], string="Product X")
    qty_x = fields.Integer("Minimum Quantity")
    product_y_id =  fields.Many2one('product.product', domain=[('available_in_pos', '=', True)], string="Product Y")
    qty_y = fields.Integer("Get Quantity")

    @api.constrains('qty_x', 'qty_y')
    def check_constrains(self):
        for data in self:
            if(data.qty_x <= 0):
                raise ValidationError('Quantity of Product should be greater than 0')
            if(data.qty_y <= 0):
                raise ValidationError('Quantity of Product should be greater than 0')

class BuyXGetDiscountOnY(models.Model):
    _name = "buy_x.get_discount_on_y"

    buy_x_get_discount_on_y_id = fields.Many2one('pos.promotions', string="Buy X Get Discount On Y")
    product_x_id = fields.Many2one('product.product', domain=[('available_in_pos', '=', True)], string="Product X")
    qty_x = fields.Integer("Minimum Quantity")
    product_y_id =  fields.Many2one('product.product', domain=[('available_in_pos', '=', True)], string="Product Y")
    discount = fields.Integer("Discount %")

    @api.constrains('qty_x', 'discount')
    def check_constrains(self):
        for data in self:
            if(data.qty_x <= 0):
                raise ValidationError('Quantity of Product should be greater than 0')
            if(data.discount < 0):
                raise ValidationError('Discount should be greater than 0')

class BuyXGetDiscountOnY(models.Model):
    _name = "discount.sale.total"

    discount_sale_total_id = fields.Many2one('pos.promotions', string="Discount On Sale Total")
    max_amount = fields.Integer("Max Sale")
    min_amount = fields.Integer("Min Sale")
    discount = fields.Integer("Discount %")

    @api.constrains('max_amount', 'min_amount', 'discount')
    def check_constrains(self):
        for data in self:
            if(data.max_amount <= 0):
                raise ValidationError('Max Sale Amount should be greater than 0')
            if(data.max_amount <= data.min_amount):
                raise ValidationError('Max Sale Amount should be greater than Min Sale Amount')
            if(data.discount < 0):
                raise ValidationError('Discount should be greater than 0')