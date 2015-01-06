from openerp.osv import osv, fields
from pprint import pprint as pp
from openerp.tools.translate import _

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'


    def import_sales_orders(self, cr, uid, job, context=None):
	storeview_obj = self.pool.get('mage.store.view')
	store_ids = storeview_obj.search(cr, uid, [('do_not_import', '=', False)])
	mappinglines = self._get_mappinglines(cr, uid, job.mapping.id)
        defaults = {}

        if job.mage_instance.invoice_policy:
            defaults.update({'order_policy': job.mage_instance.invoice_policy})

        if job.mage_instance.picking_policy:
            defaults.update({'picking_policy': job.mage_instance.picking_policy})

	for storeview in storeview_obj.browse(cr, uid, store_ids):
	    self.import_one_storeview_orders(cr, uid, job, storeview, defaults, mappinglines)

	return True


    def get_import_states(self, cr, uid, storeview, context=None):
	setup = self.pool.get('mage.setup').browse(cr, uid, 1)
	return [state.mage_order_state for state in setup.order_state_mappings
		if state.import_state
	]


    def import_one_storeview_orders(self, cr, uid, job, storeview, defaults, mappinglines=False, context=None):
	start_time = False
        if not storeview.warehouse:
            raise osv.except_osv(_('Config Error'), _('Storeview %s has no warehouse. You must assign a warehouse in order to import orders')%storeview.name)

	if storeview.import_orders_start_datetime and not \
		storeview.last_import_datetime:

	    start_time = storeview.import_orders_start_datetime

	elif storeview.last_import_datetime:
	    start_time = storeview.last_import_datetime

	states = self.get_import_states(cr, uid, storeview)

	if storeview.invoice_policy:
	    defaults.update({'order_policy': storeview.invoice_policy})

	if storeview.picking_policy:
	    defaults.update({'picking_policy': storeview.picking_policy})

	filters = {
		'store_id': {'=':storeview.external_id},
		'status': {'in': ['pending']}
	}

	if start_time:
	    filters.update({'created_at': {'gteq': start_time}})

	order_data = self._get_job_data(cr, uid, job, 'sales_order.list', [filters])
	order_ids = [x['increment_id'] for x in order_data]
	orders = self._get_job_data(cr, uid, job, 'sales_order.multiload', [order_ids])
	if not orders:
	    return True

	for order in orders:
	    order_obj = self.pool.get('sale.order')
	    order_ids = order_obj.search(cr, uid, [('external_id', '=', order['order_id'])])
	    if order_ids:
		result = self._get_job_data(cr, uid, job, 'sales_order.addComment',\
			[order['increment_id'], 'imported', 'Order Imported'])

		continue

	    try:
	        self.process_one_order(cr, uid, job, order, storeview, defaults, mappinglines)

	    except Exception, e:
		continue

	    #Set the order as pending fulfillment in Magento
	    result = self._get_job_data(cr, uid, job, 'sales_order.addComment', \
		[order['increment_id'], 'imported', 'Order Imported'])

	    #Once the order flagged in the external system, we must commit
	    #Because it is not possible to rollback in an external system
	    cr.commit()

	return True


    def process_one_order(self, cr, uid, job, order, storeview, defaults=False, mappinglines=False):
	order_obj = self.pool.get('sale.order')
	partner_obj = self.pool.get('res.partner')

	vals = order_obj.prepare_odoo_record_vals(cr, uid, job, order, storeview)

	if defaults:
	    vals.update(defaults)

	if mappinglines:
            vals.update(self._transform_record(cr, uid, job, order, 'from_mage_to_odoo', mappinglines))

	order = order_obj.create(cr, uid, vals)

        return order_obj.browse(cr, uid, order)
