from openerp.osv import osv, fields
from openerp.tools.translate import _
import xmlrpclib
from pprint import pprint as pp
from magento import Product, ProductImages, API, Order, Customer, Cart, CartCustomer, CartProduct, CartShipping, CartPayment
#TODO: Currently store id of 1 is hardcoded. What is the value of maintaining this, can it be null?

class SaleOrder(osv.osv):
    _inherit = 'sale.order'

    def create_mage_sale_order(self, cr, uid, ids, context=None):
	sale = self.browse(cr, uid, ids[0])

	#Get Username/Pass
	#TODO. Think about security here
	integrator_obj = self.pool.get('mage.integrator')
	credentials = integrator_obj.get_external_credentials(cr, uid)

	customer_data = self.prepare_mage_cart_customer_data(cr, uid, credentials, sale)
	billing_data = self.prepare_mage_cart_address_data(cr, uid, integrator_obj, credentials, sale.partner_shipping_id, 'billing')
	shipping_data = self.prepare_mage_cart_address_data(cr, uid, integrator_obj, credentials, sale.partner_shipping_id, 'shipping')

	items = self.prepare_mage_cart_items(cr, uid, sale.order_line)

	cart_id = self.create_mage_cart(credentials)
	self.add_mage_cart_customer_data(cr, uid, credentials, cart_id, customer_data, billing_data, shipping_data)
	self.add_mage_cart_item_data(cr, uid, credentials, cart_id, items)
	sale.mage_cart_id = cart_id
	if sale.carrier_id and sale.carrier_id.mage_code:
	    self.set_mage_cart_shipping_method(cr, uid, sale, credentials, cart_id)

	else:
	    print 'No Code'

	self.set_mage_cart_payment_method(cr, uid, sale, credentials, cart_id)
	result = self.mage_convert_cart_to_order(cr, uid, sale, credentials, cart_id)
	sale.mage_order_number = result
	sale.name = result
	pp(result)
#	cart_info = self.get_mage_cart_info(cr, uid, credentials, cart_id)
#	pp(cart_info)


    def set_mage_cart_shipping_method(self, cr, uid, sale, credentials, cart_id):
	try:
	    print sale.carrier_id.mage_code
            with CartShipping(credentials['url'], credentials['username'], credentials['password']) as cart_api:
#		pp(cart_api.list(cart_id, 1))
                return cart_api.method(cart_id, sale.carrier_id.mage_code, 1)
	except Exception, e:
	    raise osv.except_osv(_('Shipping Exception!'),_(str(e)))


    def set_mage_cart_payment_method(self, cr, uid, sale, credentials, cart_id):
        try:
            with CartPayment(credentials['url'], credentials['username'], credentials['password']) as cart_api:
		payment_data = {'method': 'checkmo'}
                return cart_api.method(cart_id, payment_data, 1)
        except Exception, e:
            raise osv.except_osv(_('Shipping Exception!'),_(str(e)))


    def mage_convert_cart_to_order(self, cr, uid, sale, credentials, cart_id):
        try:
            with Cart(credentials['url'], credentials['username'], credentials['password']) as cart_api:
                return cart_api.order(cart_id, 1)
        except Exception, e:
            raise osv.except_osv(_('Shipping Exception!'),_(str(e)))


    def create_mage_order_customer(self, cr, uid, credentials, sale, partner, store_id, context=None):

        firstname, lastname = self.get_name_field(cr, uid, partner)
        email = sale.order_email or partner.email or sale.partner_shipping_id.email
        if not email:
            raise osv.except_osv(_('Data Error!'),_("You must specify an Email Address"))
        try:
            with Customer(credentials['url'], credentials['username'], credentials['password']) as customer_api:
                customer = customer_api.create({'email': email,
                                        'firstname': firstname,
                                        'lastname': lastname,
                                        'website_id': store_id,
                })
                partner.external_id = customer
                print 'Created Customer in Magento with ID: %s' % customer
                #This must be committed beause the email has already been pushed to Magento
                #If the process errors out at another step, the quote/customer will be stuck
                #Because the email was pushed to Magento but the ID is not known by Odoo

                #A quote must already be saved for this action to execute, so I see no harm here
                cr.commit()
                return partner

        except Exception, e:
            raise osv.except_osv(_('Magento API Error.\nCould not create new customer with email %s.\nIf this is an existing customer, link their account.')%email,_(str(e)))


    def prepare_mage_cart_items(self, cr, uid, order_lines, context=None):
	product_data = []
        for sale_line in order_lines:
	    if not sale_line.product_id or sale_line.product_id.default_code == 'mage_shipping':
		continue

	    product_data.append({
		'product_id': sale_line.product_id.external_id,
		'qty': int(sale_line.product_uom_qty),
		'price': sale_line.price_unit,
	    })

 	return product_data


    def prepare_mage_cart_customer_data(self, cr, uid, credentials, sale, context=None):
	partner = sale.partner_id
	store_id = sale.mage_store.external_id

        firstname, lastname = self.get_name_field(cr, uid, partner)
	if not partner.external_id or partner.external_id == 0:
	    self.create_mage_order_customer(cr, uid, credentials, sale, partner, store_id)

	customer_data = {
		'mode': 'customer',
		'firstname': firstname,
		'lastname': lastname,
		'customer_id': partner.external_id,
		'website_id': 1,
		'store_id': store_id,
		'group_id': 1,
		'email': sale.order_email or sale.partner_id.email or sale.partner_shipping_id.email,
	}

	return customer_data


    def prepare_mage_cart_address_data(self, cr, uid, integrator_obj, credentials, address, address_type, context=None):
        firstname, lastname = self.get_name_field(cr, uid, address)

	shipping_data = {
		'mode': address_type,
		'telephone': address.phone,
		'firstname': firstname,
		'lastname': lastname,
		'street': address.street,
		'city': address.city,
		'region': address.state_id.name,
		'region_id': integrator_obj.get_magento_region_id(cr, uid, credentials, address.country_id.code, address.state_id.name),
		'postcode': address.zip,
		'country_id': address.country_id.code,
	}

	return [shipping_data]


    def create_mage_cart(self, credentials):
        with Cart(credentials['url'], credentials['username'], credentials['password']) as cart_api:
            return cart_api.create(1)


    def add_mage_cart_customer_data(self, cr, uid, credentials, cart_id, customer_data, billing_data, shipping_data):
        with CartCustomer(credentials['url'], credentials['username'], credentials['password']) as cartcustomer_api:
            cartcustomer_api.set(cart_id, customer_data, 1)
	    billing_data.extend(shipping_data)
            cartcustomer_api.addresses(cart_id, billing_data, 1)

	return True


    def add_mage_cart_item_data(self, cr, uid, credentials, cart_id, items):
	try:
            with CartProduct(credentials['url'], credentials['username'], credentials['password']) as cartproduct_api:
                res = cartproduct_api.add(cart_id, items, 1)

	    return True
	except xmlrpclib.Fault, e:
	    raise osv.except_osv(_('Product Error'), _(str(e)))


    def get_mage_cart_info(self, cr, uid, credentials, cart_id):
        with Cart(credentials['url'], credentials['username'], credentials['password']) as cart_api:
            return cart_api.info(cart_id)


