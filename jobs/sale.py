from openerp.osv import osv, fields
from pprint import pprint as pp
from openerp.tools.translate import _
from datetime import datetime, timedelta

DEFAULT_STATUS_FILTERS = ['processing']

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'

    def check_fba_order(self, cr, uid, record):
        #check if this is an FBA order
        if record.get('shipping_description') and 'Amazon' in record.get('shipping_description') \
		and 'Std Cont US' not in record.get('shipping_description'):
	    return True

	return False


    def import_sales_orders(self, cr, uid, job, context=None):
	storeview_obj = self.pool.get('mage.store.view')
	store_ids = storeview_obj.search(cr, uid, [('do_not_import', '=', False)])
	mappinglines = self._get_mappinglines(cr, uid, job.mapping.id)
	instance = job.mage_instance

        defaults = {}
	payment_defaults = {}

	if instance.pay_sale_if_paid:
	    payment_defaults['auto_pay'] = True
	if instance.use_invoice_date:
	    payment_defaults['invoice_backdate'] = True
	if instance.use_order_date:
	    payment_defaults['use_order_date'] = True

        if job.mage_instance.invoice_policy:
            defaults.update({'order_policy': job.mage_instance.invoice_policy})

        if job.mage_instance.picking_policy:
            defaults.update({'picking_policy': job.mage_instance.picking_policy})

	for storeview in storeview_obj.browse(cr, uid, store_ids):
	    self.import_one_storeview_orders(cr, uid, job, instance, storeview, payment_defaults, defaults, mappinglines)
	    if storeview.manual_order_number:
		storeview_obj.write(cr, uid, storeview.id, {'manual_order_number': False})
	    else:
	        storeview_obj.write(cr, uid, storeview.id, {'last_import_datetime': datetime.utcnow() - timedelta(hours=5)})

	    cr.commit()

	return True


    def import_one_storeview_orders(self, cr, uid, job, instance, storeview, payment_defaults, defaults, mappinglines=False, context=None):
	start_time = False
	picking_obj = self.pool.get('stock.picking')
	exception_obj = self.pool.get('mage.import.exception')

        if not storeview.warehouse:
            raise osv.except_osv(_('Config Error'), _('Storeview %s has no warehouse. You must assign a warehouse in order to import orders')%storeview.name)

	#This needs to be reconsidered. If there is an error, it will skip it
#	if storeview.import_orders_start_datetime and not \
#		storeview.last_import_datetime:

	start_time = storeview.import_orders_start_datetime
	end_time = storeview.import_orders_end_datetime
	skip_status = storeview.skip_order_status

	odoo_guest_customer = storeview.odoo_guest_customer
	#This field used to populate product on order if it was deleted in Magento so name can be preserved in history
	integrity_product = instance.integrity_product

	if storeview.last_import_datetime:
	    start_time = storeview.last_import_datetime

	if storeview.invoice_policy:
	    defaults.update({'order_policy': storeview.invoice_policy})

	if storeview.picking_policy:
	    defaults.update({'picking_policy': storeview.picking_policy})

	if not job.mage_instance.order_statuses and not storeview.allow_storeview_level_statuses:
	    statuses = DEFAULT_STATUS_FILTERS

	elif storeview.allow_storeview_level_statuses and storeview.order_statuses:
	    if job.mage_instance.states_or_statuses == 'state':
	        statuses = [s.mage_order_state for s in storeview.order_statuses]
	    else:
		statuses = [s.mage_order_status for s in storeview.order_statuses]
	else:
	    if job.mage_instance.states_or_statuses == 'state':
	        statuses = [s.mage_order_state for s in job.mage_instance.order_statuses]
	    else:
		statuses = [s.mage_order_status for s in job.mage_instance.order_statuses]

	filters = {
		'store_id': {'=':storeview.external_id},
	#	'status': {'in': statuses}
	}

	if start_time:
	    filters.update({'created_at': {'gteq': start_time}})

	if end_time:
	    dict = {'lteq': end_time}
	    filters.update({'CREATED_AT': dict})
	#Make the external call and get the order ids
	#Calling info is really inefficient because it loads data we dont need
	print 'Getting Order Data'

	if storeview.manual_order_number:
	    filters = {'increment_id': {'=': storeview.manual_order_number}}

	order_data = self._get_job_data(cr, uid, job, 'sales_order.search', [filters])

	if not order_data:
	    return True

	#The following code needs a proper implementation,
	#However this code will be very fast in excluding unnecessary orders
	#and do a good job of pre-filtering

	order_basket = []
	order_ids = [x['increment_id'] for x in order_data]
#	order_ids = ['10042648']

	for id in order_ids:
	    new_val = "('" + id + "')"
	    order_basket.append(new_val)

	val_string = ','.join(order_basket)
	if not val_string:
	    return True
	query = """WITH increments AS (VALUES %s) \
		SELECT column1 FROM increments \
		LEFT OUTER JOIN sale_order ON \
		(increments.column1 = sale_order.mage_order_number) \
		WHERE sale_order.mage_order_number IS NULL""" % val_string
	cr.execute(query)

	res = cr.fetchall()
	increment_ids = [z[0] for z in res]
	increment_ids.sort()
	increment_ids = order_ids
	print increment_ids
	datas = [increment_ids[i:i+300] for i in range(0, len(increment_ids), 300)]

	for dataset in datas:
	    try:
	        orders = self._get_job_data(cr, uid, job, 'sales_order.multiload', [dataset])
	    except Exception, e:
		print 'Could not retrieve multiple order info'
		continue

	    if not orders:
		print 'No Orders'
	        continue

	    skip_items = ['ggmnotship', 'ggmnoship', 'ggmdropship', 'ggmrma']
	    for order in orders:
		skip_order = False
		#GG mod, skip certain orders
		for i in order['items']:
		    if i.get('sku') and i.get('sku').lower() in skip_items:
			skip_order = True
			break

		if skip_order:
		    continue
#		    print 'Marketplace Order'
#		    try:
#		        status = self.set_one_order_status(cr, uid, job, order, 'o_complete', 'Marketplace Order')
#			continue
#		    except Exception, e:
#			continue
		
		#TODO: Add proper logging and debugging
	        order_obj = self.pool.get('sale.order')
	        order_ids = order_obj.search(cr, uid, [('mage_order_number', '=', order['increment_id'])])
	        if order_ids:
#		    if not skip_status:
#		        status = self.set_one_order_status(cr, uid, job, order, 'imported', 'Order Imported')

#		    print 'Skipping existing order %s' % order['increment_id']
		    continue

		#Assign guest checkout orders to odoo customer if applicable
		if not order.get('customer_email') and order.get('customer_id') == '0' and odoo_guest_customer:
		    order['odoo_customer_id'] = odoo_guest_customer.id

	        try:
	            sale_order = self.process_one_order(cr, uid, job, order, storeview, payment_defaults, defaults, integrity_product, mappinglines)
#		    sale_order.action_button_confirm()
		    fba_order = self.check_fba_order(cr, uid, order)
		    if fba_order:
			self.confirm_one_order(cr, uid, sale_order)
			self.mage_status_complete(cr, uid, sale_order)

#		    if order['status'] not in ['pending', 'new', 'complete']:
#		        #All orders must go to Shipworks
#		        self.confirm_one_order(cr, uid, sale_order)

		    #If the order is complete upon import, decrement inventory immediately
		    if order['status'] == 'complete':
			picking_ids = picking_obj.search(cr, uid, [('sale', '=', sale_order.id)])
			if picking_ids:
			    for picking in picking_obj.browse(cr, uid, picking_ids):
				if picking.state == 'draft':
				    picking_obj.action_confirm(cr, uid, [picking.id], context=context)
				if picking.state != 'assigned':
                                    picking_obj.force_assign(cr, uid, [picking.id])
                                picking.do_transfer()
			else:
                            self.confirm_one_order(cr, uid, sale_order)
                            self.mage_status_complete(cr, uid, sale_order)
#		    if order['status'] in ['pending', 'new']:
 #                       picking_ids = picking_obj.search(cr, uid, [('sale', '=', sale_order.id)])
  #                      if picking_ids:
#			    sale.state = 'manual'
 #                           for picking in picking_obj.browse(cr, uid, picking_ids):
#				if picking.state == 'done':
#				    continue
 #                               if picking.state in ['partially_available', 'assigned']:
  #                                  picking_obj.do_unreserve(cr, uid, picking.id)
#
 #                               picking_obj.action_cancel(cr, uid, picking.id)
  #                              picking.reset_picking_draft()
   #                             procurement_obj = self.pool.get('procurement.order')
    #                            procurement_ids = procurement_obj.search(cr, uid, [('group_id', '=', picking.group_id.id)])
     #                           if procurement_ids:
      #                              procurement_obj.write(cr, uid, procurement_ids, {'state': 'confirmed'})
#
#				picking_obj.write(cr, uid, [picking.id], {'sw_exp': False})

		    #Check if this order is subject to special conditions (Grow Green)
		    amazon = self.identify_amazon_order(cr, uid, order)
		    if amazon:
			order_obj.write(cr, uid, sale_order.id, {'amazon_process': True})

		    #Check if the order is a child of a canceled order
		    if order.get('relation_parent_id') and order.get('increment_id')[-2:] == '-1':
			to_cancel_ids = self.pool.get('sale.order').search(cr, uid, [('external_id', '=', order['relation_parent_id'])])
			if to_cancel_ids:
			    for cancel_order in self.pool.get('sale.order').browse(cr, \
				uid, to_cancel_ids
				):
				self.cancel_one_order(cr, uid, job, cancel_order, sale_order)
				
		    #Implement something to auto approve if configured
#		    sale_order.action_button_confirm()

	        except Exception, e:
		    print 'Exception', e
		    exception_obj.create(cr, uid, {
						'external_id': order['increment_id'],
						'message': str(e),
						'data': str(order),
						'type': 'Sale Order',
						'job': job.id,
		    })
		    print 'Exception Processing Order with Id: %s' % order['increment_id'], e
		    continue

		if not skip_status:
#		    status = self.set_one_order_status(cr, uid, job, order, 'o_complete', 'Order Imported')
		    if not status:
		        print 'Created order but could not notify Magento'

		print 'Successfully Imported order with ID: %s' % order['increment_id']
	            #Once the order flagged in the external system, we must commit
	            #Because it is not possible to rollback in an external system

	        cr.commit()

	return True


    def process_one_order(self, cr, uid, job, order, storeview, payment_defaults, defaults=False, integrity_product=False, mappinglines=False):
	order_obj = self.pool.get('sale.order')
	partner_obj = self.pool.get('res.partner')

	vals = order_obj.prepare_odoo_record_vals(cr, uid, job, order, payment_defaults, defaults, integrity_product, storeview)

	if mappinglines:
            vals.update(self._transform_record(cr, uid, job, order, 'from_mage_to_odoo', mappinglines))

	vals['order_policy'] = 'manual'
	sale_order = order_obj.create(cr, uid, vals)
        return order_obj.browse(cr, uid, sale_order)


    def set_one_order_status(self, cr, uid, job, order, status, message, context=None):
	try:
            result = self._get_job_data(cr, uid, job, 'sales_order.addComment',\
		[order['increment_id'], status, message])
	    return True

	except Exception, e:
	    print 'Status Exception', e
	    return False


    def confirm_one_order(self, cr, uid, sale):
	#What all steps can this apply to
	if sale.state == 'draft':
	    sale.action_button_confirm()
	    

    def cancel_one_order(self, cr, uid, job, sale, new_sale):
	exception_obj = self.pool.get('mage.import.exception')
        cant_process = False
        if sale.picking_ids:
            print 'This order has pickings'

	picking_obj = self.pool.get('stock.picking')
	sale_obj = self.pool.get('sale.order')
        if sale.picking_ids:
            for picking in sale.picking_ids:
                if picking.state == 'done':
                    cant_process = True
                    print 'This order cannot be canceled'
                    break

                if picking.state in ['partially_available', 'assigned']:
                    picking_obj.do_unreserve(cr, uid, picking.id)
                    picking_obj.action_cancel(cr, uid, picking.id)
                else:
                    picking_obj.action_cancel(cr, uid, picking.id)
                picking_obj.unlink(cr, uid, picking.id)

        sale_obj.action_cancel(cr, uid, sale.id)
	if new_sale:
	    sale_obj.write(cr, uid, new_sale, {'canceled_order_failed': cant_process, \
		'canceled_sale_order': sale.id})

        return True

		picking_obj.write(cr, uid, [picking.id], {'sw_exp': False, 'sw_pre_exp': False})
#                picking_obj.unlink(cr, uid, picking.id)
        if cant_process:
            exception_obj.create(cr, uid, {
                'external_id': sale.external_id,
                'message': 'This order cannot be canceled because at least one of its pickings is done',
                'data': """{'order': %s, 'reason': %s}""" % (sale.mage_order_number, 'Picking already done'),
                'type': 'Sale Order',
                'job': job.id,
            })
	    return True

        sale_obj.action_cancel(cr, uid, sale.id)
	if new_sale:
	    sale_obj.write(cr, uid, new_sale.id, {'canceled_order_failed': cant_process, \
		'canceled_sale_order': sale.id})

        return True


    def identify_amazon_order(self, cr, uid, order):
	amazon = False
	if order['status'] == 'Amazon_New':
	    amazon = True
	#Identify by order level
#	if True:
#	    amazon = True

	#Identify at item level
#	for product in order['items']:
	    #Add check at line level
#	    if True:
#		amazon = True
	return amazon
