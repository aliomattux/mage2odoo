from openerp.osv import osv, fields
from pprint import pprint as pp

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'

    def ship_mage_orders(self, cr, uid, job, context=None):
	#This implementation is not good nor adaptable. This will need a rework
	package_obj = self.pool.get('stock.out.package')
        storeview_obj = self.pool.get('mage.store.view')
        store_ids = storeview_obj.search(cr, uid, [('do_not_import', '=', False)])
        for storeview in storeview_obj.browse(cr, uid, store_ids):
	    package_ids = self.get_pending_packages(cr, uid, storeview.id)
	    for package in package_obj.browse(cr, uid, package_ids):
		if package.picking.sale.mage_shipment_complete and package.picking.external_id:
		    result = self.send_one_package(cr, uid, job, package.picking.external_id, package, True)
		else:
		    shipping_id = self.send_one_package(cr, uid, job, package.picking.sale.mage_order_number, package, False)
		    if shipping_id:
			package.picking.external_id = shipping_id
			package.picking.mage_export_error = False
			package.mage_package_state = 'done'
			if not package.picking.sale.mage_shipment_complete:
			    package.picking.sale.mage_shipment_complete = True

		    else:
			package.mage_package_state = 'exception'
			package.picking.mage_export_error = True

        return True


    #This is a temoporary method. Ideal solution does not involve a direct sql query
    def get_pending_packages(self, cr, uid, storeview_id):
	query = "SELECT package.id" \
		" FROM stock_out_package package" \
		" JOIN stock_picking picking ON (package.picking = picking.id)" \
		" JOIN delivery_carrier carrier ON (picking.carrier_id = carrier.id)" \
		" JOIN sale_order sale ON (sale.id = picking.sale)" \
		" WHERE package.mage_package_state = 'pending'" \
		" AND sale.mage_store = %s LIMIT 100" % storeview_id

        cr.execute(query)
        return [id[0] for id in cr.fetchall()]


    def send_one_package(self, cr, uid, job, incrementid, package, track_only):
	#This is yucky business
	base_carrier = package.picking.carrier_id.mage_carrier

	if track_only:
	    try:
		response = self._get_job_data(cr, uid, job, \
			'sales_order_shipment.addTrack', [incrementid, base_carrier, \
			'Shipped', package.tracking_number])
		print 'RESPONSE', response
	    except Exception, e:
		return False
	else:
            try:
		response = self._get_job_data(cr, uid, job, \
                	'sales_order_invoice.create_tracking', [incrementid, False, \
                        False, False, package.tracking_number, base_carrier, 'Shipped'])
		print 'RESPONSE', response
            except Exception, e:
		return False


        return response


    #This is a temoporary method. Ideal solution does not involve a direct sql query
    def get_pending_invoices(self, cr, uid, storeview_id):
	query = "SELECT rel.order_id, rel.invoice_id" \
		"\nFROM sale_order_invoice_rel rel" \
		"\nJOIN sale_order sale ON (sale.id = rel.order_id)" \
		"\nJOIN account_invoice invoice ON (invoice.id = rel.invoice_id)" \
		"\nWHERE invoice.state = 'paid'" \
		"\nAND invoice.mage_export_error IS NOT True" \
		"\nAND sale.mage_invoice_complete IS NOT True" \
		"\nAND sale.mage_store = %s" % storeview_id

	cr.execute(query)
	return cr.dictfetchall()


    def sync_invoices(self, cr, uid, job, context=None):
        storeview_obj = self.pool.get('mage.store.view')
        store_ids = storeview_obj.search(cr, uid, [('do_not_import', '=', False)])
	for storeview in storeview_obj.browse(cr, uid, store_ids):
	    invoice_data = self.get_pending_invoices(cr, uid, storeview.id)
	    if invoice_data:
		self.send_invoices(cr, uid, job, invoice_data)

	return True


    def send_invoices(self, cr, uid, job, invoice_data):
	invoice_obj = self.pool.get('account.invoice')
	sale_obj = self.pool.get('sale.order')
	for collection in invoice_data:


	    invoice = invoice_obj.browse(cr, uid, collection['invoice_id'])
	    sale = sale_obj.browse(cr, uid, collection['order_id'])
	    comment = 'Payment Captured'
	    if sale.mage_invoice_complete:
		continue

	    try:
                mage_id = self._get_job_data(cr, uid, job, \
                    'sales_order_invoice.capture_create', [sale.mage_order_number, comment, False, False])
	        sale.mage_invoice_complete = True
		print 'Successfully Created and Captured Invoice in Magento'

	    except Exception, e:
		print 'Error', e
		invoice.mage_export_error = True


	return True
