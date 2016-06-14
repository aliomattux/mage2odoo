from openerp.osv import osv, fields
from pprint import pprint as pp
from openerp.tools.translate import _
from datetime import datetime, timedelta

class saleOrder(osv.osv):
    _inherit = 'sale.order'
    _columns = {
	'mage_shipment_code': fields.char('Magento Shipping Code'),
	'mage_custom_status': fields.char('Magento Custom Status'),
    }


class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'

    def update_odoo_orders(self, cr, uid, job):
	""" See if order status is changed in Magento. If so then update it in Odoo
	"""
        storeview_obj = self.pool.get('mage.store.view')
        store_ids = storeview_obj.search(cr, uid, [('do_not_import', '=', False)])
        mappinglines = self._get_mappinglines(cr, uid, job.mapping.id)
        instance = job.mage_instance
	#Get a list of all orders updated in the last 24 hours
	from_date = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
	sale_obj = self.pool.get('sale.order')
	picking_obj = self.pool.get('stock.picking')
	for storeview in storeview_obj.browse(cr, uid, store_ids):
            filters = {
                'store_id': {'=':storeview.external_id},
                'status': {'updated_at': {'gt': from_date}}
            }

	    #Get list of IDS
	    order_data = self._get_job_data(cr, uid, job, 'sales_order.search', [filters])
	    if not order_data:
		return True
	
	    #For each order in the response of orders updated
	    for order in order_data:
		increment_id = order['increment_id']

		#Check Magento Status
		status = order.get('status')
		if not status:
		    continue

		#Find sales in Odoo that match the given idd
		sale_ids = sale_obj.search(cr, uid, [('mage_order_number', '=', increment_id)])
		if sale_ids:
		    sale = sale_obj.browse(cr, uid, sale_ids[0])
		    #If the status in Odoo is not the same as Magento
		    if sale.mage_custom_status != status:
			print 'Setting Custom Status'
			sale.mage_custom_status = status

		    #If order is canceled
		    if status == 'canceled':
			self.cancel_one_order(cr, uid, job, sale)

		    #TODO: Add handling for orders completely shipped in Odoo


                    #If order can be fulfilled
                    if status in ['Picking'] and sale.state in ['draft']:
			self.confirm_one_order(cr, uid, sale)
