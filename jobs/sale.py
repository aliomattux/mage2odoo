from openerp.osv import osv, fields
from pprint import pprint as pp
from openerp.tools.translate import _
from datetime import datetime

DEFAULT_STATUS_FILTERS = ['processing']

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'


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
	    self.import_one_storeview_orders(cr, uid, job, storeview, payment_defaults, defaults, mappinglines)
	    storeview_obj.write(cr, uid, storeview.id, {'last_import_datetime': datetime.utcnow()})
	    cr.commit()

	return True


    def import_one_storeview_orders(self, cr, uid, job, storeview, payment_defaults, defaults, mappinglines=False, context=None):
	start_time = False
        if not storeview.warehouse:
            raise osv.except_osv(_('Config Error'), _('Storeview %s has no warehouse. You must assign a warehouse in order to import orders')%storeview.name)

	#This needs to be reconsidered. If there is an error, it will skip it
#	if storeview.import_orders_start_datetime and not \
#		storeview.last_import_datetime:

	start_time = storeview.import_orders_start_datetime

#	elif storeview.last_import_datetime:
#	    start_time = storeview.last_import_datetime

	if storeview.invoice_policy:
	    defaults.update({'order_policy': storeview.invoice_policy})

	if storeview.picking_policy:
	    defaults.update({'picking_policy': storeview.picking_policy})

	if not job.mage_instance.order_statuses and not storeview.allow_storeview_level_statuses:
	    statuses = DEFAULT_STATUS_FILTERS
	elif storeview.allow_storeview_level_statuses and storeview.order_statuses:
	    statuses = [s.mage_order_state for s in storeview.order_statuses]
	else:
	    statuses = [s.mage_order_state for s in job.mage_instance.order_statuses]

	filters = {
		'store_id': {'=':storeview.external_id},
		'status': {'in': statuses}
	}


	if start_time:
	    filters.update({'created_at': {'gteq': start_time}})

	#Make the external call and get the order ids
	order_data = self._get_job_data(cr, uid, job, 'sales_order.list', [filters])

	if not order_data:
	    return True

	order_ids = [x['increment_id'] for x in order_data]

	datas = [order_ids[i:i+300] for i in range(0, len(order_ids), 300)]
	for dataset in datas:
	    try:
	        orders = self._get_job_data(cr, uid, job, 'sales_order.multiload', [dataset])
	    except Exception, e:
		print 'Could not retrieve multiple order info'
		continue

	    if not orders:
	        continue

	    for order in orders:
		#TODO: Add proper logging and debugging
#		pp(order)

	        order_obj = self.pool.get('sale.order')
	        order_ids = order_obj.search(cr, uid, [('external_id', '=', order['order_id'])])
	        if order_ids:
		    status = self.set_one_order_status(cr, uid, job, order, 'imported', 'Order Imported')
		    print 'Skipping existing order %s' % order['increment_id']
		    continue

	        try:
	            sale_order = self.process_one_order(cr, uid, job, order, storeview, payment_defaults, defaults, mappinglines)
		    #Implement something to auto approve if configured
#		    sale_order.action_button_confirm()

	        except Exception, e:
		    print 'Exception Processing Order with Id: %s' % order['increment_id'], e
		    continue

		status = self.set_one_order_status(cr, uid, job, order, 'imported', 'Order Imported')

		if status:
		    print 'Successfully Imported order with ID: %s' % order['increment_id']
	            #Once the order flagged in the external system, we must commit
	            #Because it is not possible to rollback in an external system
		else:
		    print 'Created order but could not notify Magento'

	        cr.commit()

	return True


    def process_one_order(self, cr, uid, job, order, storeview, payment_defaults, defaults=False, mappinglines=False):
	order_obj = self.pool.get('sale.order')
	partner_obj = self.pool.get('res.partner')

	vals = order_obj.prepare_odoo_record_vals(cr, uid, job, order, payment_defaults, storeview)

	if defaults:
	    vals.update(defaults)

	if mappinglines:
            vals.update(self._transform_record(cr, uid, job, order, 'from_mage_to_odoo', mappinglines))


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
