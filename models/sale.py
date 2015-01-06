from openerp.osv import osv, fields
from pprint import pprint as pp

class SaleOrder(osv.osv):
    _inherit = 'sale.order'
    _columns = {
	'mage_store': fields.many2one('mage.store.view', 'Magento Store'),
	'order_email': fields.char('Magento Email', readonly=True),
	'ip_address': fields.char('IP Address'),
	'mage_order_total': fields.float('Magento Order Total', copy=False),
	'mage_order_number': fields.char('Magento Order Number', select=True),
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


    def prepare_odoo_record_vals(self, cr, uid, job, record, storeview=False):
	partner_obj = self.pool.get('res.partner')

        if record['customer_id']:
            partner = partner_obj.get_or_create_customer(cr, uid, record)

	else:
	    record['customer_id'] = 0
	    partner = partner_obj.get_or_create_customer(cr, uid, record)

        invoice_address = partner_obj.get_or_create_partner_address(cr, uid, \
                record['billing_address'], partner,
        )

        if type(record['payment']) != dict:
	    raise osv.except_osv(_('Error!'),_(""))

        payment_method = self.get_mage_payment_method(cr, \
                uid, record['payment']
        )

        vals = {
                'mage_order_number': record['increment_id'],
#               'order_policy':
#               'note':
                'partner_invoice_id': invoice_address.id,
                'order_email': record['customer_email'],
                'partner_id': partner.id,
                'date_order': record['created_at'],
                'payment_method': payment_method.id,
#               'state':
#               'pricelist_id':
                'ip_address': record['x_forwarded_for'],
		'order_line': self.prepare_odoo_line_record_vals(cr, uid, job, record),
                'mage_order_total': record['grand_total'],
                'external_id': record['order_id'],
        }

	if storeview:
            if storeview.order_prefix:
                ordernumber = storeview.order_prefix + record['increment_id']

            else:
                ordernumber = record['increment_id']

            vals.update({'name': ordernumber,
                         'mage_store': storeview.id,
                         'warehouse_id': storeview.warehouse.id,
            })


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
                cr, uid, record
                )
            )

        if float(record.get('discount_amount')):
            vals['order_line'].append(
                self.get_discount_line_data_using_magento_data(
                cr, uid, record
                )
            )

	return vals


    def prepare_odoo_line_record_vals(
        self, cr, uid, job, order, context=None
    ):
        """Make data for an item line from the magento data.
        This method decides the actions to be taken on different product types
        :return: List of data of order lines in required format
        """
        product_obj = self.pool.get('product.product')

        line_data = []
        for item in order['items']:
            if not item['parent_item_id']:

                # If its a top level product, create it
                values = {
                    'name': item['name'],
                    'price_unit': float(item['price']),
   #                 'product_uom':
    #                    website_obj.get_default_uom(
     #                       cursor, user, context
      #              ).id,
                    'product_uom_qty': float(item['qty_ordered']),
                  #  'magento_notes': item['product_options'],
#                    'type': 'make_to_order',
                    'product_id': product_obj.get_or_create_odoo_record(
                                cr, uid, job, item['product_id']
                    ).id
                }

                if order['tax_identification']:
                    taxes = self.get_mage_taxes(cr, uid, order['tax_identification'], item)
                    values['tax_id'] = [(6, 0, taxes)]

                line_data.append((0, 0, values))

            # If the product is a child product of a bundle product, do not
            # create a separate line for this.
            if 'bundle_option' in item['product_options'] and \
                    item['parent_item_id']:
                continue

        return line_data


    def get_shipping_line_data_using_magento_data(
        self, cr, uid, order, context=False
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
        return (0, 0, {
            'name': 'Magento Shipping',
            'price_unit': float(order.get('shipping_incl_tax', 0.00)),
            'product_uom': 1,
  #          'tax_id': [(6, 0, taxes)],
          #  'magento_notes': ' - '.join([
           #     order['shipping_method'],
            #    order['shipping_description']
           # ])
        })


    def get_discount_line_data_using_magento_data(
        self, cr, uid, order, context=False
    ):
        """
        Create a discount line for the given sale using magento data

        :param cursor: Database cursor
        :param user: ID of current user
        :param order_data: Order Data from magento
        :param context: Application context
        """

        return (0, 0, {
            'name': 'Discount - ' + order['discount_description'] or 'Magento Discount',
            'price_unit': float(order.get('discount_amount', 0.00)),
            'product_uom': 1,
#            'magento_notes': order_data['discount_description'],
        })




    def get_mage_taxes(self, cr, uid, taxes, item_data, context=None):
        """Match the tax in openerp with the tax rate from magento
        Use this tax on sale line
        """
        tax_obj = self.pool.get('account.tax')
        # Magento does not return the name of tax
        # First try matching with the percent
        tax_amount = item_data['tax_percent']
        for tax in taxes:
            for rate in tax['rates']:
                if float(rate['percent']) == float(tax_amount):
                    tax_name = rate['title']
                    tax_code = rate['code']

        tax_ids = tax_obj.search(cr, uid, [
        ('name', '=', tax_name),
        ])

        if not tax_ids:
            vals = {
                    'amount': float(item_data['tax_percent']) / 100,
                    'mage_tax': True,
                    'name': tax_name,
                    'description': tax_code,
            }

            tax = tax_obj.create(cr, uid, vals)
            tax_ids = [tax]

        # FIXME This will fail in the case of bundle products as tax comes
        # comes with the children and not with parent
        return tax_ids
