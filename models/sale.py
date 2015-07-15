from openerp.osv import osv, fields
from pprint import pprint as pp

class SaleOrder(osv.osv):
    _inherit = 'sale.order'
    _columns = {
	'mage_store': fields.many2one('mage.store.view', 'Magento Store'),
	'order_email': fields.char('Magento Email', readonly=True),
	'ip_address': fields.char('IP Address'),
	'mage_order_total': fields.float('Magento Order Total', copy=False, readonly=True),
	'mage_paid_total': fields.float('Magento Total Paid', help="This is the amount pre-paid", copy=False, readonly=True),
        'mage_order_status': fields.char('Magento Order Status', copy=False, readonly=True),
        'mage_order_prepaid': fields.boolean('Magento Order Pre-paid', copy=False, readonly=True),
        'mage_paid_date': fields.datetime('Magento Paid Date', copy=False, readonly=True),
	'mage_order_number': fields.char('Magento Order Number', select=True, readonly=True),
	'mage_invoice_id': fields.integer('Magento Invoice Id', copy=False, select=True),
	'packages': fields.one2many('stock.out.package', 'sale', 'Packages', copy=False),
	'external_id': fields.integer('External Id', copy=False, select=True),
	'mage_shipment_complete': fields.boolean('Magento Shipment Complete', readonly=True, copy=False),
	'mage_invoice_complete': fields.boolean('Magento Billing Complete', readonly=True, copy=False),
    }


    def get_mage_payment_method(self, cr, uid, payment, context=None):
	mage_method = payment.get('method')
	payment_obj = self.pool.get('payment.method')
	method = payment_obj.search(cr, uid, [('mage_code', '=', mage_method)])
	if method:
	    return payment_obj.browse(cr, uid, method[0])

	else:
	    vals = {
		'name': mage_method,
		'mage_code': mage_method,
	    }
	    return payment_obj.browse(cr, uid, payment_obj.create(cr, uid, vals))


    def get_mage_shipping_method(self, cr, uid, job, record, context=None):
        carrier_obj = self.pool.get('delivery.carrier')
	carrier = carrier_obj.get_mage_record(cr, uid, record['code'])
	if not carrier:
	    vals = carrier_obj.prepare_odoo_record_vals(cr, uid, job, record)
            return carrier_obj.browse(cr, uid, carrier_obj.create(cr, uid, vals))
	else:
	    return carrier_obj.browse(cr, uid, carrier)


    def get_mage_payment_details(self, cr, uid, job, record, payment_defaults, context=None):
	vals = {
		'mage_order_total': record['grand_total'],
	}
        if record['total_paid'] == record['grand_total'] or \
		record['total_due'] == '0.0000' and record['state'] == 'complete':
	    vals['mage_invoice_complete'] = True
	    vals['mage_order_prepaid'] = True
	    #Find effective way to determine paid date
	    vals['mage_paid_date'] = record['created_at']
	    vals['mage_paid_total'] = record['total_paid']

	    #This is implemented to avoid having to create an invoice from picking
	    #Automatically. This could have unpredictable behavior
	    if payment_defaults.get('auto_pay'):
		vals['order_policy'] = 'prepaid'

	#TODO: To be replaced by status mapping
	if record['state'] in ['canceled', 'closed']:
	    vals['state'] = 'cancel'

	if record['state'] == 'complete':
	    vals['mage_shipment_complete'] = True

	return vals
	    

    def prepare_odoo_record_vals(self, cr, uid, job, record, payment_defaults, \
		defaults, storeview=False
	):
	    
	partner_obj = self.pool.get('res.partner')

        if record['customer_id']:
            partner = partner_obj.get_or_create_customer(cr, uid, record)

	else:
	    record['customer_id'] = 0
	    partner = partner_obj.get_or_create_customer(cr, uid, record)

        invoice_address = partner_obj.get_or_create_partner_address(cr, uid, \
                record['billing_address'], partner,
        )

	if record.get('payment'):
            if type(record['payment']) != dict:
	        raise osv.except_osv(_('Error!'),_(""))

            payment_method = self.get_mage_payment_method(cr, \
                    uid, record['payment']
            )
	else:
	    payment_method = False


	if record.get('tax_identification'):
	    rates = self.get_order_tax_rates(cr, uid, record['tax_identification'])
	    if not rates:
		raise
	else:
	    rates = False

        vals = {
		'mage_order_status': record['state'],
                'mage_order_number': record['increment_id'],
#               'order_policy':
#               'note':
                'partner_invoice_id': invoice_address.id,
                'order_email': record['customer_email'],
                'partner_id': partner.id,
                'date_order': record['created_at'],
                'payment_method': payment_method.id if payment_method else None,
#               'state':
#               'pricelist_id':
                'ip_address': record.get('x_forwarded_for'),
		'order_line': self.prepare_odoo_line_record_vals(cr, uid, job, record, rates),
                'external_id': record.get('order_id'),
        }

	if defaults:
	    vals.update(defaults)

        if payment_defaults.get('use_order_date'):
            vals['date_order'] = record['created_at']
            vals['create_date'] = record['created_at']

	if storeview:
            if storeview.order_prefix:
                ordernumber = storeview.order_prefix + record['increment_id']

            else:
                ordernumber = record['increment_id']

            vals.update({'name': ordernumber,
                         'mage_store': storeview.id,
                         'warehouse_id': storeview.warehouse.id,
            })

	#Payment and order totals
	vals.update(self.get_mage_payment_details(cr, uid, job, record, payment_defaults))

        if record['shipping_method']:
	    shipping_record = {'code': record['shipping_method'], 
				'label': record['shipping_description']
	    }
            delivery_method = self.get_mage_shipping_method( \
                    cr, uid, job, shipping_record
            )
            vals.update({'carrier_id': delivery_method.id})

        if record.get('shipping_address'):
            shipping_address = partner_obj.get_or_create_partner_address(cr, uid, \
                    record['shipping_address'], partner,
            )
            vals.update({'partner_shipping_id': shipping_address.id})

        if float(record.get('shipping_amount')):
            vals['order_line'].append(
                self.get_shipping_line_data_using_magento_data(
                cr, uid, record, rates
                )
            )

        if record.get('discount_amount'):
            vals['order_line'].append(
                self.get_discount_line_data_using_magento_data(
                cr, uid, record
                )
            )
	return vals


    def prepare_odoo_line_record_vals(
        self, cr, uid, job, order, rates, context=None
    ):
        """Make data for an item line from the magento data.
        This method decides the actions to be taken on different product types
        :return: List of data of order lines in required format
        """
        product_obj = self.pool.get('product.product')

        line_data = []
        for item in order['items']:

	    if item['product_type'] == 'simple' or not item['product_type']:
                values = {
                    'name': item['name'] or item['sku'],
                    'price_unit': float(item['price']),
   #                 'product_uom':
    #                    website_obj.get_default_uom(
     #                       cursor, user, context
      #              ).id,
                    'product_uom_qty': float(item['qty_ordered']),
                  #  'magento_notes': item['product_options'],
#                    'type': 'make_to_order',
                    'product_id': product_obj.get_or_create_odoo_record(
                                cr, uid, job, item['product_id'], item=item,
                    ).id
                }

		tax_percent = item.get('tax_percent')
                if rates and tax_percent and float(tax_percent) > 0.001:
                    taxes = self.get_mage_taxes(cr, uid, rates, item)
                    values['tax_id'] = [(6, 0, taxes)]

                line_data.append((0, 0, values))

            # If the product is a child product of a bundle product, do not
            # create a separate line for this.
            if item.get('product_options') and 'bundle_option' in item['product_options'] and \
                    item['parent_item_id']:
                continue

        return line_data


    def get_shipping_line_data_using_magento_data(
        self, cr, uid, order, rates, context=False
    ):
        """
        Create a shipping line for the given sale using magento data

        :param cursor: Database cursor
        :param user: ID of current user
        :param order_data: Order Data from magento
        :param context: Application context
        """

#        taxes = self.get_magento_shipping_tax(
#            cr, uid, order, context
 #       )
	#Solves bug where free shipping is none type

	if order.get('shipping_amount'):
	    shipping_amount = float(order.get('shipping_amount'))
	    total_amount = order.get('shipping_incl_tax')
	    tax = order.get('shipping_tax_amount')
	else:
	    shipping_amount = 0.00

	vals = {'name': 'Magento Shipping',
            'price_unit': shipping_amount,
            'product_uom': 1,
        }

	tax_percentage = False

	if tax and total_amount:
	    tax_percentage = round((float(total_amount)- shipping_amount) / shipping_amount, 2) * 100

        if rates and tax_percentage and float(tax_percentage) > 0.001:
            taxes = self.get_mage_taxes(cr, uid, rates, item_data={'tax_percent': tax_percentage})
            vals['tax_id'] = [(6, 0, taxes)]

        return (0, 0, vals)


    def get_discount_line_data_using_magento_data(
        self, cr, uid, order, context=False
    ):
        """
        Create a discount line for the given sale using magento data

        """
	if order['discount_description']:
	    description = order['discount_description']
	else:
	    description = 'Discount'
	if order.get('discount_amount'):
	    amount = float(order.get('discount_amount'))
	else:
	    amount = 0
        return (0, 0, {
            'name': 'Discount - ' + description,
            'price_unit': amount,
            'product_uom': 1,
#            'magento_notes': order_data['discount_description'],
        })


    def get_order_tax_rates(self, cr, uid, taxes):
        rates = []
        all_rates = []
        for tax in taxes:
	    all_rates.append(float(tax['percent']))
            rates.append({'code': tax['id'],
                        'title': tax['id'],
                        'percent': float(tax['percent'])
            })
        return {'rates': rates, 'all': round(sum(all_rates), 2)}


    def get_mage_taxes(self, cr, uid, taxes, item_data, context=None):
        """Match the tax in openerp with the tax rate from magento
        Use this tax on sale line
        """
	tax_amount = float(item_data['tax_percent'])
        tax_obj = self.pool.get('account.tax')
	all_tax = False
	order_tax_ids = []
	test_rates = []
	if taxes['all'] == round(tax_amount, 2):
	    all_tax = True

	for tax in taxes['rates']:

	    if not all_tax and tax['percent'] != item_data['tax_percent']:
		continue

            tax_name = tax['title']
            tax_code = tax['code']
            tax_ids = tax_obj.search(cr, uid, [
		('name', '=', tax_name),
	    ])

            if not tax_ids:
                vals = {
                        'amount': float(tax['percent']) / 100,
                        'mage_tax': True,
                        'name': tax_name,
                        'description': tax_code,
                }

                tax_id = tax_obj.create(cr, uid, vals)

	    else:
		 tax_id = tax_ids[0]

            order_tax_ids.append(tax_id)
            # FIXME This will fail in the case of bundle products as tax comes
            # comes with the children and not with parent

        return order_tax_ids
