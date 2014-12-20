from openerp.osv import osv, fields
from pprint import pprint as pp

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'

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
