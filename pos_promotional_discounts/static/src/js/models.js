odoo.define('pos_promotional_discounts.models', function (require) {
    "use strict";
	var models = require('point_of_sale.models');
	var SuperOrderline = models.Orderline.prototype;
    var SuperOrder = models.Order.prototype;
    var core = require('web.core');
	var _t = core._t;

    models.load_fields('res.partner',['pos_order_count'])
	models.load_fields('pos.session',['customer_count','order_count'])
	models.load_fields('product.product',['wk_promo_messages'])
	models.load_fields('pos.category',['wk_promo_messages'])
	
	// -------load promo_message mode and ir_sequence model-------
	models.load_models([{
			model: 'pos.promotions',
			fields: [],
			domain: function(self){ 
				return [['id','in', self.config.promo_message_ids],['active','=',true]]; 
			},
			loaded: function(self,promo_messages){
				self.db.all_promo_message = promo_messages;
				self.db.all_promotions_by_id = {};
				self.db.promotions_by_sequence_id = {};
				self.db.promotions_squence = [];
				_.each(self.db.all_promo_message, function(data){
                    self.db.promotions_squence.push(data.sequence)
                    self.db.all_promotions_by_id[data.id] = data
                    self.db.promotions_by_sequence_id[data.sequence] = data
                })
			},
        },{
            model: 'discount.products',
            fields: [],
            domain: function(self){
                var ids = []
                _.each(self.db.all_promo_message, function(item){
                    if(item.offer_type == "discount_on_products"){
                        if(item.discounted_ids.length){
                            _.each(item.discounted_ids, function(data){
                                ids.push(data)
                            })
                        }
                    }
                })
                return [['id', 'in', ids]];
            },
            loaded: function(self, result){
                self.db.discount_items = result;
                self.db.discount_product = result;
                self.db.discount_product_by_id = []
                _.each(self.db.discount_product, function(data){
					self.db.discount_product_by_id[data.product_id[0]] = data
                })
            }
        },{
			model: 'buy_x.get_y',
            fields: [],
            domain: function(self){
                var ids = []
                _.each(self.db.all_promo_message, function(item){
                    if(item.offer_type == "buy_x_get_y"){
                        if(item.buy_x_get_y_ids.length){
                            _.each(item.buy_x_get_y_ids, function(data){
                                ids.push(data)
                            })
                        }
                    }
                })
                return [['id', 'in', ids]];
            },
			loaded: function(self,result){
                self.db.buy_x_get_y = result;
                self.db.buy_x_get_y_by_id = [];
                _.each(self.db.buy_x_get_y, function(data){
					self.db.buy_x_get_y_by_id[data.product_x_id[0]] = data
                })
			},
		},{
			model: 'buy_x.get_y_qty',
            fields: [],
            domain: function(self){
                var ids = []
                _.each(self.db.all_promo_message, function(item){
                    if(item.offer_type == "buy_x_get_y_qty"){
                        if(item.buy_x_get_y_qty_ids.length){
                            _.each(item.buy_x_get_y_qty_ids, function(data){
                                ids.push(data)
                            })
                        }
                    }
                })
                return [['id', 'in', ids]];
            },
			loaded: function(self,result){
                self.db.buy_x_get_y_qty = result;
                self.db.buy_x_get_y_qty_by_id = {};
                _.each(self.db.buy_x_get_y_qty, function(data){
					self.db.buy_x_get_y_qty_by_id[data.id] = data
                })
			},
		},{
			model: 'buy_x.get_discount_on_y',
            fields: [],
            domain: function(self){
                var ids = []
                _.each(self.db.all_promo_message, function(item){
                    if(item.offer_type == "buy_x_get_discount_on_y"){
                        if(item.buy_x_get_discount_on_y_ids.length){
                            _.each(item.buy_x_get_discount_on_y_ids, function(data){
                                ids.push(data)
                            })
                        }
                    }
                })
                return [['id', 'in', ids]];
            },
			loaded: function(self,result){
                self.db.buy_x_get_discount_on_y = result;
                self.db.buy_x_get_discount_on_y_by_id = [];
                _.each(self.db.buy_x_get_discount_on_y, function(data){
					self.db.buy_x_get_discount_on_y_by_id[data.product_x_id[0]] = data
                })
			},
		},{
			model: 'discount.sale.total',
            fields: [],
            domain: function(self){
                var ids = []
                _.each(self.db.all_promo_message, function(item){
                    if(item.offer_type == "get_x_discount_on_sale_total"){
                        if(item.discount_sale_total_ids.length){
                            _.each(item.discount_sale_total_ids, function(data){
                                ids.push(data)
                            })
                        }
                    }
                })
                return [['id', 'in', ids]];
            },
			loaded: function(self,result){
				self.db.discounted_rules= result;
			},
		}
    ]);

    var SuperPosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        set_order: function(order) {
            SuperPosModel.set_order.call(this, order);
            if (order.is_offer_applied){
                $('.apply_promotions .fa.fa-gift').css({"color":"#6EC89B"});
            } else {
                $('.apply_promotions .fa.fa-gift').css({"color":"white"});
            }
        },
    });

    models.Orderline = models.Orderline.extend({
        initialize: function(attr,options){
            var self = this;
            self.data = this.wk_offer_tag()
            self.is_offer_product = options.is_offer_product || false
            self.is_buy_x_get_y_product = options.is_buy_x_get_y_product || false
            self.is_buy_x_get_y__qty_product = options.is_buy_x_get_y__qty_product || false
			self.is_discount_product = options.is_discount_product || false
			self.free_product = options.free_product || false
			self.is_discounted_product = options.is_discounted_product || false
			self.related_product_id = options.related_product_id || false
            self.is_buy_x_get_discount_on_y = options.is_buy_x_get_discount_on_y || false
			SuperOrderline.initialize.call(this,attr,options)
        },
        wk_offer_tag: function(){
            if (this.is_discount_product){
                return 'Order Discount'
            } else if (this.is_discounted_product || this.is_buy_x_get_discount_on_y && this.pos) {
                return 'Discounted Product'
            } else if(this.is_buy_x_get_y_product && this.pos) {
                return 'Extra Product of ' + this.pos.db.product_by_id[this.related_product_id].display_name
            } else if(this.is_buy_x_get_y__qty_product && this.pos) {
                return 'Extra Product of ' + this.pos.db.product_by_id[this.related_product_id].display_name
            } else {
                return false
            }
        },
        export_as_JSON:function(){
            var self = this;
            var loaded=SuperOrderline.export_as_JSON.call(this);
            loaded.is_offer_product = self.is_offer_product || false
            loaded.is_buy_x_get_y_product = self.is_buy_x_get_y_product || false
            loaded.is_buy_x_get_y__qty_product = self.is_buy_x_get_y__qty_product || false
			loaded.is_discount_product = self.is_discount_product || false
			loaded.free_product = self.free_product || false
			loaded.is_discounted_product = self.is_discounted_product || false
			loaded.related_product_id = self.related_product_id || false
            loaded.related_product_ids = self.related_product_ids || false
            return loaded;
        },
        export_for_printing: function(){
            var self = this;
            var loaded = SuperOrderline.export_for_printing.call(this);
            loaded.data = this.wk_offer_tag()
            return loaded
        },
        set_quantity: function(quantity, keep_price){
            var self = this;
            var previos_qty = self.quantity || 0;
            var product = self.product;
            var order = self.pos.get_order();

            SuperOrderline.set_quantity.call(this,quantity,keep_price);

            var offers = null;
            if(order && order.is_offer_applied){
                offers = self.get_all_promotions(order)
                if (!self.is_offer_product){
                    if(offers){
                        var product = self.product
                        var options = {}
                        var apply_offer = self.apply_offer(offers, product);
                        if (apply_offer){
                            if(apply_offer == 'discount_on_products'){
                                self.is_discounted_product = true;
                                self.is_offer_product = true
                                var discount_val = self.get_discount_val(offers, product);
                                if(discount_val){
                                    setTimeout(function(){
                                        self.set_discount(discount_val);
                                    }, 250)
                                }
                            }
                            else if (apply_offer == 'buy_x_get_y'){
                                var can_apply_buy_x_get_y = order.can_apply_buy_x_get_y(offers, apply_offer,order,product,options, self)
                                if (can_apply_buy_x_get_y){
                                    if(previos_qty == 0){
                                        order.remove_orderline(self.id);
                                        order.add_buy_x_get_y(offers, apply_offer,order,product,options,self);
                                    }
                                    else{
                                        order.add_buy_x_get_y(offers, apply_offer,order,product,options,self); 
                                    }
                                }
                            }
                            else if (apply_offer == 'buy_x_get_y_qty'){
                                var can_apply_buy_x_get_y_qty = order.can_apply_buy_x_get_y_qty(offers, apply_offer,order,product,options, self)
                                if (can_apply_buy_x_get_y_qty){
                                    if(previos_qty == 0){
                                        order.remove_orderline(self.id);
                                        order.add_buy_x_get_y_qty(offers, apply_offer,order,product,options,self);
                                    }
                                    else{
                                        order.add_buy_x_get_y_qty(offers, apply_offer,order,product,options,self); 
                                    }
                                }
                            }
                            else if (apply_offer == 'buy_x_get_discount_on_y'){
                                var can_apply_buy_x_get_discount_on_y = order.can_apply_buy_x_get_discount_on_y(offers, apply_offer,order,product,options, self)
                                if (can_apply_buy_x_get_discount_on_y){
                                    if(previos_qty == 0){
                                        order.remove_orderline(self.id);
                                        order.buy_x_get_discount_on_y(offers, apply_offer,order,product,options,self);
                                    }
                                    else{
                                        order.buy_x_get_discount_on_y(offers, apply_offer,order,product,options,self);
                                    }
                                }
                                else{
                                    // Check if discount can be applied
                                    order.check_and_apply_discount_offer(offers, apply_offer,order,product,options, self)
                                }
                            }
                        }
                    }
                }
                if(order.get_total_with_tax() <= 0){
                    _.each(offers, function(promo){
                        if (promo){
                            if (promo.offer_type == "get_x_discount_on_sale_total"){
                                if (promo.discount_product_id && promo.discount_product_id[0]){
                                    var orderlines = order.get_orderlines();
                                    _.each(orderlines, function(line){
                                        if(line.product.id == promo.discount_product_id[0]){
                                            order.remove_orderline(line)
                                        }
                                    }) 
                                }
                            }
                        }
                    })
                }
            }
        },
        get_discount_val: function(offers, product){
            var self = this;
            if (product){
                var discount_val = 0
                var flag = false
                _.each(self.pos.db.promotions_by_sequence_id, function(promotions){
					if(promotions.offer_type == 'discount_on_products'){
                        _.each(self.pos.db.discount_items, function(item){
                            if(promotions.discounted_ids.includes(item.id)){
                                if(!flag && item.apply_on == "1_products"){
                                    if(item.product_id[0] == product.id){
                                        discount_val = item.percent_discount
                                        flag = true
                                    } 
                                }
                                if(!flag && item.apply_on == "2_categories"){
                                    if(item.categ_id[0] == product.categ_id[0]){
                                        discount_val = item.percent_discount
                                        flag = true
                                    }
                                }
                                if(!flag && item.apply_on == "3_all"){
                                    discount_val = item.percent_discount
                                    flag = true
                                }
                            }
                        })       
                    }
                });
                return discount_val
            }
        },
        apply_offer: function(offers, product){
            var self = this
            var apply_offer = null;
            _.each(offers, function(offer){
                if (!apply_offer){
                    if(offer.offer_type == 'discount_on_products'){
                        var flag = false
                        _.each(self.pos.db.discount_items, function(item){
                            if(offer.discounted_ids.includes(item.id)){
                                if(!flag && item.apply_on == "1_products"){
                                    if(item.product_id[0] == product.id){
                                        flag = true
                                    } 
                                }
                                if(!flag && item.apply_on == "2_categories"){
                                    if(item.categ_id[0] == product.categ_id[0]){
                                        flag = true
                                    }
                                }
                                if(!flag && item.apply_on == "3_all"){
                                    flag = true
                                }
                            }
                        })
                        if (flag){
                            apply_offer = 'discount_on_products'
                        }
                    }
                }
                if (!apply_offer){
                    if(offer.offer_type == 'buy_x_get_y'){
                        if(self.pos.db.buy_x_get_y.length){
                            _.each(self.pos.db.buy_x_get_y, function(item){
                                if(offer.buy_x_get_y_ids.includes(item.id)){
                                    if (item.product_x_id[0] == product.id)
                                        apply_offer = 'buy_x_get_y'
                                }
                            })
                        }
                    }
                }
                if (!apply_offer){
                    if(offer.offer_type == 'buy_x_get_y_qty'){
                        if(self.pos.db.buy_x_get_y_qty.length){
                            _.each(self.pos.db.buy_x_get_y_qty, function(item){
                                if(offer.buy_x_get_y_qty_ids.includes(item.id)){
                                    if (item.product_x_id[0] == product.id)
                                        apply_offer = 'buy_x_get_y_qty'
                                }
                            })
                        }
                    }
                }
                if (!apply_offer){
                    if(offer.offer_type == 'buy_x_get_discount_on_y'){
                        if(self.pos.db.buy_x_get_discount_on_y.length){
                            _.each(self.pos.db.buy_x_get_discount_on_y, function(item){ 
                                if(offer.buy_x_get_discount_on_y_ids.includes(item.id)){
                                    if (item.product_x_id[0] == product.id)
                                        apply_offer = 'buy_x_get_discount_on_y'
                                    if (item.product_y_id[0] == product.id)
                                        apply_offer = 'buy_x_get_discount_on_y'
                                }
                            })
                        }
                    }
                }
            })
            return apply_offer
        },
        get_all_promotions: function(order){
			var self = this;
			var all_promotions = self.pos.db.promotions_by_sequence_id;
			var current_order = order;
			var client = current_order.get_client();
			var promo_messages_dict = {};
            var promo_message_list = [];
            if (order){
                var all_order_lines = order.get_orderlines();
                _.each(all_promotions,function(promo_message){
                    if(client && promo_message.criteria_type == 'every_new_customer'){
                        if(client.pos_order_count == '0'){
                            promo_messages_dict[promo_message.sequence] = promo_message;
                        }
                    }
                    else if(promo_message.criteria_type == 'every_x_order'){
                        if(self.pos.pos_session.order_count%promo_message.order_number == 0)
                            promo_messages_dict[promo_message.sequence] = promo_message;
                    }
                    else if(client && promo_message.criteria_type == 'first_x_customer'){
                        if(self.pos.pos_session.customer_count < promo_message.no_of_customers)
                            promo_messages_dict[promo_message.sequence] = promo_message;
                    }
                    else if(promo_message.criteria_type == 'specific_items'){
                        _.find(all_order_lines,function(line){
                            if(line.product.wk_promo_messages && (jQuery.inArray(promo_message.id,line.product.wk_promo_messages)>= 0)){
                                promo_messages_dict[promo_message.sequence] = promo_message;
                                return true;
                            }
                        });		
                    }
                    else if(promo_message.criteria_type == 'specific_categ'){
                        _.find(all_order_lines,function(line){
                            if(line.product.pos_categ_id){
                                var pos_categ = self.pos.db.category_by_id[line.product.pos_categ_id[0]]
                                if(jQuery.inArray(promo_message.id,pos_categ.wk_promo_messages)>= 0){
                                    promo_messages_dict[promo_message.sequence] = promo_message;
                                    return true;
                                }
                            }
                        });	
                    }
                    else if(promo_message.criteria_type == 'every_order'){
                        promo_messages_dict[promo_message.sequence] = promo_message;
                    }
                    else if(promo_message.criteria_type == 'based_specific_date'){
                        var today_date = new Date();
                        if(today_date.getDate() == promo_message.wk_day && (today_date.getMonth()+1) == promo_message.wk_month)
                            promo_messages_dict[promo_message.sequence] = promo_message[promo_message.id] = promo_message;
                    } 
                });
                if (promo_messages_dict)
                    promo_message_list = _.map(promo_messages_dict,function(value,key){ return value});
                return promo_message_list
            }
		},
        check_if_offer_can_be_applied: function(){
			var self = this;
			var exist = false
            var product_id = self.product.id;
            if (self.pos.config.show_offers_in_orderline){
                if(self.pos.db.discount_items){
                    var flag = false
                    var discount_val = 0
                    if (product_id){
                        var product = self.pos.db.product_by_id[product_id];
                        _.each(self.pos.db.discount_items, function(item){
                            var promo = self.pos.db.all_promotions_by_id[item.discount_product_id[0]]
                            if (promo && promo.criteria_type == 'based_specific_date'){
                                var today_date = new Date();
                                if(today_date.getDate() == promo.wk_day && (today_date.getMonth()+1) == promo.wk_month){
                                    if(!flag && item.apply_on == "1_products"){
                                        if(item.product_id[0] == product.id){
                                            discount_val = item.percent_discount
                                            flag = true
                                        } 
                                    }
                                    if(!flag && item.apply_on == "2_categories"){
                                        if(item.categ_id[0] == product.categ_id[0]){
                                            discount_val = item.percent_discount
                                            flag = true
                                        }
                                    }
                                    if(!flag && item.apply_on == "3_all"){
                                        discount_val = item.percent_discount
                                        flag = true
                                    }
                                    if(flag){
                                        exist = true
                                    }
                                }
                            }
                            else if (promo && promo.criteria_type == 'every_x_order') {
                                if(self.pos.pos_session.order_count%promo.order_number == 0){
                                    if(!flag && item.apply_on == "1_products"){
                                        if(item.product_id[0] == product.id){
                                            discount_val = item.percent_discount
                                            flag = true
                                        } 
                                    }
                                    if(!flag && item.apply_on == "2_categories"){
                                        if(item.categ_id[0] == product.categ_id[0]){
                                            discount_val = item.percent_discount
                                            flag = true
                                        }
                                    }
                                    if(!flag && item.apply_on == "3_all"){
                                        discount_val = item.percent_discount
                                        flag = true
                                    }
                                    if(flag){
                                        exist = true
                                    }
                                }
                            }
                            else{
                                if(!flag && item.apply_on == "1_products"){
                                    if(item.product_id[0] == product.id){
                                        discount_val = item.percent_discount
                                        flag = true
                                    } 
                                }
                                if(!flag && item.apply_on == "2_categories"){
                                    if(item.categ_id[0] == product.categ_id[0]){
                                        discount_val = item.percent_discount
                                        flag = true
                                    }
                                }
                                if(!flag && item.apply_on == "3_all"){
                                    discount_val = item.percent_discount
                                    flag = true
                                }
                                if(flag){
                                    exist = true
                                }
                            }
                        });
                    }
                }
                if(self.pos.db.buy_x_get_y){
                    _.each(self.pos.db.buy_x_get_y, function(item){
                        if(item.product_x_id[0] == product_id){
                            exist = true
                        }
                    })
                }
                if(self.pos.db.buy_x_get_y_qty){
                    _.each(self.pos.db.buy_x_get_y_qty, function(item){
                        if(item.product_x_id[0] == product_id){
                            exist = true
                        }
                    })
                }
                if(self.pos.db.buy_x_get_discount_on_y){
                    _.each(self.pos.db.buy_x_get_discount_on_y, function(item){
                        if(item.product_x_id[0] == product_id){
                            exist = true
                        }
                    })
                }
                return exist
            }else{
                return false
            }
		},
    })

    models.Order = models.Order.extend({
        initialize: function(attributes,options){
            var self = this;
            SuperOrder.initialize.call(this,attributes, options);
            self.is_offer_applied = options.is_offer_applied || true
        },
        add_product: function(product, options){
            var self = this;
            SuperOrder.add_product.call(this,product, options);
            var order = self.pos.get_order();
            if(self.pos && self.pos.config && order.is_offer_applied){
                var order = self.pos.get_order();
                var promo_message_list = self.get_all_promotions(order);
                if (promo_message_list.length){
                    _.each(promo_message_list, function(promo){
                        if (promo){
                            if (promo.offer_type == "get_x_discount_on_sale_total"){
                                if (promo.discount_product_id && promo.discount_product_id[0]){
                                    setTimeout(function(){ 
                                        var discount_product_id = promo.discount_product_id[0]
                                        var order    = self.pos.get_order();
                                        let val = self.get_discount(order.get_total_with_tax());
                                        // self.apply_discount(val, promo.discount_product_id[0])

                                        var lines    = order.get_orderlines();
                                        var product  = self.pos.db.get_product_by_id(discount_product_id);
                                        
                                        if (product === undefined) {
                                            // ---- There is no Discount Product
                                            return;
                                        }
                                
                                        // Remove existing discounts
                                        var i = 0;
                                        while ( i < lines.length ) {
                                            if (lines[i].get_product() === product) {
                                                order.remove_orderline(lines[i]);
                                            } else {
                                                i++;
                                            }
                                        }
                                        
                                        var base_to_discount = order.get_total_without_tax();
                                        if (product.taxes_id.length){
                                            var first_tax = self.pos.taxes_by_id[product.taxes_id[0]];
                                            if (first_tax.price_include) {
                                                base_to_discount = order.get_total_with_tax();
                                            }
                                        }
                                        var discount = - val / 100.0 * base_to_discount;
                                        if( discount < 0 ){
                                            if (discount_product_id){
                                                var line = new models.Orderline({}, {pos: self.pos, order: order, product: product,quantity:1, price: discount, lst_price: discount ,is_promo_offer_product:true, is_discount_product:true});   
                                                line.price = discount
                                                line.lst_price = discount
                                                self.orderlines.add(line);
                                                order.selected_orderline.price_manually_set = true;
                                            }
                                        }
                                    }, 250);    
                                }
                            }
                        }
                    })
                }
            }
        },
        get_discount: function(sale_total){
            var discount = 0;
			var self = this;
			_.each(self.pos.db.discounted_rules, function(rule){
				if (!discount){
					if (sale_total > rule.min_amount && sale_total < rule.max_amount){
						discount = rule.discount
					}
				}
			})
			return discount
		},
        get_all_promotions: function(order){
			var self = this;
			var all_promotions = self.pos.db.promotions_by_sequence_id;
			var current_order = order;
			var client = current_order.get_client();
			var promo_messages_dict = {};
            var promo_message_list = [];
            if (order){
                var all_order_lines = order.get_orderlines();
                _.each(all_promotions,function(promo_message){
                    if(client && promo_message.criteria_type == 'every_new_customer'){
                        if(client.pos_order_count == '0'){
                            promo_messages_dict[promo_message.id] = promo_message;
                        }
                    }
                    else if(promo_message.criteria_type == 'every_x_order'){
                        if(self.pos.pos_session.order_count%promo_message.order_number == 0)
                            promo_messages_dict[promo_message.id] = promo_message;
                    }
                    else if(client && promo_message.criteria_type == 'first_x_customer'){
                        if(self.pos.pos_session.customer_count < promo_message.no_of_customers)
                            promo_messages_dict[promo_message.id] = promo_message;
                    }
                    else if(promo_message.criteria_type == 'specific_items'){
                        _.find(all_order_lines,function(line){
                            if(line.product.wk_promo_messages && (jQuery.inArray(promo_message.id,line.product.wk_promo_messages)>= 0)){
                                promo_messages_dict[promo_message.id] = promo_message;
                                return true;
                            }
                        });		
                    }
                    else if(promo_message.criteria_type == 'specific_categ'){
                        _.find(all_order_lines,function(line){
                            if(line.product.pos_categ_id){
                                var pos_categ = self.pos.db.category_by_id[line.product.pos_categ_id[0]]
                                if(jQuery.inArray(promo_message.id,pos_categ.wk_promo_messages)>= 0){
                                    promo_messages_dict[promo_message.id] = promo_message;
                                    return true;
                                }
                            }
                        });	
                    }
                    else if(promo_message.criteria_type == 'every_order'){
                        promo_messages_dict[promo_message.id] = promo_message;
                    }
                    else if(promo_message.criteria_type == 'based_specific_date'){
                        var today_date = new Date();
                        if(today_date.getDate() == promo_message.wk_day && (today_date.getMonth()+1) == promo_message.wk_month)
                            promo_messages_dict[promo_message.id] = promo_message[promo_message.id] = promo_message;
                    } 
                });
                if (promo_messages_dict)
                    promo_message_list = _.map(promo_messages_dict,function(value,key){ return value});
    
                return promo_message_list
            }
		},
        apply_discount: function(val, discount_product_id) {
			var self = this;
			var order    = this.pos.get_order();
            var lines    = order.get_orderlines();
			var product  = this.pos.db.get_product_by_id(discount_product_id);
            
            if (product === undefined) {
                // 
                // ---- There is no Discount Product
                // 

				// this.showPopup('ErrorPopup', {
				// 	title : _t("No discount product found"),
				// 	body  : _t("The discount product seems misconfigured. Make sure it is flagged as 'Can be Sold' and 'Available in Point of Sale'."),
				// });
				return;
			}
	
			// Remove existing discounts
			var i = 0;
			while ( i < lines.length ) {
				if (lines[i].get_product() === product) {
					order.remove_orderline(lines[i]);
				} else {
					i++;
				}
			}
			
			// Add discount
			// We add the price as manually set to avoid recomputation when changing customer.
			var base_to_discount = order.get_total_without_tax();
			if (product.taxes_id.length){
				var first_tax = this.pos.taxes_by_id[product.taxes_id[0]];
				if (first_tax.price_include) {
					base_to_discount = order.get_total_with_tax();
				}
			}
			var discount = - val / 100.0 * base_to_discount;
			if( discount < 0 ){
				if (discount_product_id){
                    var line = new models.Orderline({}, {pos: self.pos, order: order, product: product,quantity:1, price: discount, lst_price: discount ,is_offer_product:true, is_discount_product:true});   
                    line.price = discount
                    line.lst_price = discount
                    self.orderlines.add(line);
                    order.selected_orderline.price_manually_set = true;
				}
			}
        },
        check_and_apply_discount_offer: function(offers, apply_offer,order,product,options, active_line){
            var offer_product_id = null
            var discount = 0
            var self = this;
            self.pos.db.buy_x_get_discount_on_y.forEach(function(item){
                if (item.product_y_id[0] == product.id){
                    offer_product_id = item.product_x_id[0]
                    discount = item.discount
                }
            })
            if (offer_product_id){
                var offer_product = self.pos.db.product_by_id[offer_product_id]
                if (offer_product){
                    var offer_can_be_applied = self.can_apply_buy_x_get_discount_on_y(offers, apply_offer,order,offer_product,options, active_line)
                    if (offer_can_be_applied){
                        setTimeout(function(){ 
                            order.selected_orderline.set_discount(discount)
                            order.selected_orderline.is_offer_product = true
                            order.selected_orderline.related_product_id = offer_product.id
                            order.selected_orderline.is_buy_x_get_discount_on_y = true
                        }, 200);
                    }
                }
            }
        },
        can_apply_buy_x_get_discount_on_y: function(offers, apply_offer,order,product,options, active_line){
            var self = this;
            var orderlines = order.get_orderlines();
            var count_qty = 0;
            var has_extra = false;
            if(apply_offer){
                var found = false
                orderlines.forEach(function(orderline){
                    if(orderline.cid == active_line.cid)
                        found = true;
                    if(orderline.is_offer_product == false){
                        if(orderline.is_buy_x_get_discount_on_y == false){
                            if(orderline.product.id == product.id){
                                count_qty += orderline.quantity
                            }
                        }
                    }
                });

                if(!found){
                    if(active_line.is_offer_product == false){
                        if(active_line.is_buy_x_get_discount_on_y == false){
                            if(active_line.product.id == product.id){
                                count_qty += active_line.quantity
                            }
                        }
                    }
                }
                // -------------------------------------------------------------------
                var wk_apply_offer = null;
                _.each(offers, function(offer){
                    if (!wk_apply_offer){
                        if(offer.offer_type == 'buy_x_get_discount_on_y'){
                            if(self.pos.db.buy_x_get_discount_on_y.length){
                                _.each(self.pos.db.buy_x_get_discount_on_y, function(item){
                                    if(offer.buy_x_get_discount_on_y_ids.includes(item.id)){
                                        if (item.product_x_id[0] == product.id){
                                            wk_apply_offer = item
                                        }
                                    }
                                })
                            }
                        }
                    }
                })
                // -------------------------------------------------------------------
                if(wk_apply_offer){
                    if(count_qty >= wk_apply_offer.qty_x){
                        return true
                    }
                    else{
                        orderlines.forEach(function(orderline){
                            if(orderline.related_product_id == product.id){
                                orderline.set_discount(0);
                                orderline.is_buy_x_get_discount_on_y = false
                            }
                        });
                        return false
                    }
                }
                else
                    return false
            }
            else
                return false
        },
        can_apply_buy_x_get_y_qty: function(offers, apply_offer,order,product,options, active_line){
            var self = this;
            var orderlines = order.get_orderlines();
            var count_qty = 0;
            var has_extra = false;
            if(apply_offer){
                var found = false
                orderlines.forEach(function(orderline){
                    if(orderline.cid == active_line.cid)
                        found = true;
                    if(orderline.is_offer_product == false){
                        if(orderline.is_buy_x_get_y__qty_product == false){
                            if(orderline.product.id == product.id){
                                count_qty += orderline.quantity
                            }
                        }
                    }
                });

                if(!found){
                    if(active_line.is_offer_product == false){
                        if(active_line.is_buy_x_get_y__qty_product == false){
                            if(active_line.product.id == product.id){
                                count_qty += active_line.quantity
                            }
                        }
                    }
                }

                // -------------------------------------------------------------------
                var wk_apply_offer = null;
                _.each(offers, function(offer){
                    if (!wk_apply_offer){
                        if(offer.offer_type == 'buy_x_get_y_qty'){
                            if(self.pos.db.buy_x_get_y_qty.length){
                                _.each(self.pos.db.buy_x_get_y_qty, function(item){
                                    if(offer.buy_x_get_y_qty_ids.includes(item.id)){
                                        if (item.product_x_id[0] == product.id){
                                            wk_apply_offer = item
                                        }
                                    }
                                })
                            }
                        }
                    }
                })
                // -------------------------------------------------------------------

                if(wk_apply_offer){
                    if(count_qty >= wk_apply_offer.qty_x){
                        return true
                    }
                    else{
                        orderlines.forEach(function(orderline){
                            if(orderline.related_product_id == product.id){
                                order.remove_orderline(orderline.id);
                            }
                        });
                        return false
                    }
                }
                else
                    return false
            }
            else
                return false
        },
        buy_x_get_discount_on_y: function(offers, apply_offer,order,product,options,active_line){
            var self = this;
            var count_qty = 0
            var found = false
            var old_orderline = null;

            order.get_orderlines().forEach(function(orderline){
                if(orderline.related_product_id == product.id){
                    old_orderline = orderline
                }
                if(active_line)
                    if(orderline.cid == active_line.cid)
                        found = true;

                if(orderline.is_offer_product == false)
                    if(orderline.is_buy_x_get_y_product == false)
                        if(orderline.product.id == product.id)
                            count_qty += orderline.quantity
            });

            if(active_line){
                if(!found){
                    if(active_line.is_offer_product == false){
                        if(active_line.is_buy_x_get_y_product == false){
                            if(active_line.product.id == product.id){
                                count_qty += active_line.quantity
                            }
                        }
                    }
                }
            }

            var buy_x_get_discount_on_y_qty = 1
            var buy_x_get_discount_product = null
            var discount = 0
            // -------------------------------------------------------------------
            var wk_apply_offer = null;
            _.each(offers, function(offer){
                if (!wk_apply_offer){
                    if(offer.offer_type == 'buy_x_get_discount_on_y'){
                        if(self.pos.db.buy_x_get_discount_on_y.length){
                            _.each(self.pos.db.buy_x_get_discount_on_y, function(item){
                                if(offer.buy_x_get_discount_on_y_ids.includes(item.id)){
                                    if (item.product_x_id[0] == product.id){
                                        wk_apply_offer = item
                                    }
                                }
                            })
                        }
                    }
                }
            })
            // -------------------------------------------------------------------
            if(wk_apply_offer){
                buy_x_get_discount_on_y_qty = Math.floor(wk_apply_offer.qty_x)
                buy_x_get_discount_product = self.pos.db.product_by_id[wk_apply_offer.product_y_id[0]]
                discount = wk_apply_offer.discount
            }

            if(old_orderline){
                old_orderline.set_discount(discount)
                // old_orderline.set_unit_price(0)
            }
            else{
                if(discount){
                    if(buy_x_get_discount_on_y_qty){
                        var orderlines = order.get_orderlines();
                        orderlines.forEach(function(orderline){
                            if(orderline.product.id == buy_x_get_discount_product.id){
                                orderline.set_discount(discount)
                                orderline.is_offer_product = true
                                orderline.related_product_id = product.id
                                orderline.is_buy_x_get_discount_on_y = true
                            }
                        });
                    }
                }
            }
        },
        add_buy_x_get_y_qty: function(offers,apply_offer,order,product,options,active_line){
            var self = this;
            var count_qty = 0
            var found = false
            var old_orderline = null;

            order.get_orderlines().forEach(function(orderline){
                if(orderline.related_product_id == product.id){
                    old_orderline = orderline
                }
                if(active_line)
                    if(orderline.cid == active_line.cid)
                        found = true;

                if(orderline.is_offer_product == false)
                    if(orderline.is_buy_x_get_y__qty_product == false)
                        if(orderline.product.id == product.id)
                            count_qty += orderline.quantity
            });

            if(active_line){
                if(!found){
                    if(active_line.is_offer_product == false){
                        if(active_line.is_buy_x_get_y__qty_product == false){
                            if(active_line.product.id == product.id){
                                count_qty += active_line.quantity
                            }
                        }
                    }
                }
            }

            var buy_x_get_y_product_qty = 1
            var buy_x_get_y_product = null
            // -------------------------------------------------------------------
            var wk_apply_offer = null;
            _.each(offers, function(offer){
                if (!wk_apply_offer){
                    if(offer.offer_type == 'buy_x_get_y_qty'){
                        if(self.pos.db.buy_x_get_y_qty.length){
                            _.each(self.pos.db.buy_x_get_y_qty, function(item){
                                if(offer.buy_x_get_y_qty_ids.includes(item.id)){
                                    if (item.product_x_id[0] == product.id){
                                        wk_apply_offer = item
                                    }
                                }
                            })
                        }
                    }
                }
            })
            // -------------------------------------------------------------------
            if(wk_apply_offer){
                buy_x_get_y_product_qty = (Math.floor(count_qty/wk_apply_offer.qty_x) * wk_apply_offer.qty_y)
                buy_x_get_y_product = self.pos.db.product_by_id[wk_apply_offer.product_y_id[0]]
            }

            if(old_orderline){
                old_orderline.set_quantity(buy_x_get_y_product_qty)
                old_orderline.set_unit_price(0)
            }
            else{
                if(buy_x_get_y_product){
                    if(buy_x_get_y_product_qty){
                        var line = new models.Orderline({}, {pos: self.pos, order: order, product: buy_x_get_y_product, quantity:buy_x_get_y_product_qty, is_offer_product:true, is_buy_x_get_y__qty_product:true, related_product_id: product.id});
                        line.price = 0
                        line.quantity = buy_x_get_y_product_qty;   
                        line.quantityStr = '' + buy_x_get_y_product_qty.toFixed(2);   
                        self.orderlines.add(line);
                    }
                }
            }
        },
        can_apply_buy_x_get_y: function(offers, apply_offer,order,product,options, active_line){
            var self = this;
            var orderlines = order.get_orderlines();
            var count_qty = 0;
            var has_extra = false;
            if(apply_offer){
                var found = false
                orderlines.forEach(function(orderline){
                    if(orderline.cid == active_line.cid)
                        found = true;
                    if(orderline.is_offer_product == false){
                        if(orderline.is_buy_x_get_y_product == false){
                            if(orderline.product.id == product.id){
                                count_qty += orderline.quantity
                            }
                        }
                    }
                });

                if(!found){
                    if(active_line.is_offer_product == false){
                        if(active_line.is_buy_x_get_y_product == false){
                            if(active_line.product.id == product.id){
                                count_qty += active_line.quantity
                            }
                        }
                    }
                }

                // -------------------------------------------------------------------
                var wk_apply_offer = null;
                _.each(offers, function(offer){
                    if (!wk_apply_offer){
                        if(offer.offer_type == 'buy_x_get_y'){
                            if(self.pos.db.buy_x_get_y.length){
                                _.each(self.pos.db.buy_x_get_y, function(item){
                                    if(offer.buy_x_get_y_ids.includes(item.id)){
                                        if (item.product_x_id[0] == product.id){
                                            wk_apply_offer = item
                                        }
                                    }
                                })
                            }
                        }
                    }
                })
                // -------------------------------------------------------------------

                if(wk_apply_offer){
                    if(count_qty >= wk_apply_offer.qty_x){
                        return true
                    }
                    else{
                        orderlines.forEach(function(orderline){
                            if(orderline.related_product_id == product.id){
                                order.remove_orderline(orderline.id);
                            }
                        });
                        return false
                    }
                }
                else
                    return false
            }
            else
                return false
        },
        add_buy_x_get_y: function(offers, apply_offer,order,product,options,active_line){
            var self = this;
            var count_qty = 0
            var found = false
            var old_orderline = null;

            order.get_orderlines().forEach(function(orderline){
                if(orderline.related_product_id == product.id){
                    old_orderline = orderline
                }
                if(active_line)
                    if(orderline.cid == active_line.cid)
                        found = true;

                if(orderline.is_offer_product == false)
                    if(orderline.is_buy_x_get_y_product == false)
                        if(orderline.product.id == product.id)
                            count_qty += orderline.quantity
            });

            if(active_line){
                if(!found){
                    if(active_line.is_offer_product == false){
                        if(active_line.is_buy_x_get_y_product == false){
                            if(active_line.product.id == product.id){
                                count_qty += active_line.quantity
                            }
                        }
                    }
                }
            }

            var buy_x_get_y_product_qty = 1
            var buy_x_get_y_product = null
            // -------------------------------------------------------------------
            var wk_apply_offer = null;
            _.each(offers, function(offer){
                if (!wk_apply_offer){
                    if(offer.offer_type == 'buy_x_get_y'){
                        if(self.pos.db.buy_x_get_y.length){
                            _.each(self.pos.db.buy_x_get_y, function(item){
                                if(offer.buy_x_get_y_ids.includes(item.id)){
                                    if (item.product_x_id[0] == product.id){
                                        wk_apply_offer = item
                                    }
                                }
                            })
                        }
                    }
                }
            })
            // -------------------------------------------------------------------
            if(wk_apply_offer){
                buy_x_get_y_product_qty = Math.floor(count_qty/wk_apply_offer.qty_x)
                buy_x_get_y_product = self.pos.db.product_by_id[wk_apply_offer.product_y_id[0]]
            }

            if(old_orderline){
                old_orderline.set_quantity(buy_x_get_y_product_qty)
                old_orderline.set_unit_price(0)
            }
            else{
                if(buy_x_get_y_product){
                    if(buy_x_get_y_product_qty){
                        var line = new models.Orderline({}, {pos: self.pos, order: order, product: buy_x_get_y_product, quantity:buy_x_get_y_product_qty, is_offer_product:true, is_buy_x_get_y_product:true, related_product_id: product.id});
                        line.price = 0
                        line.quantity = buy_x_get_y_product_qty;
                        line.quantityStr = '' + buy_x_get_y_product_qty.toFixed(2);   
                        self.orderlines.add(line);
                    }
                }
            }
        },
    });
});