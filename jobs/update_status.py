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

    def update_odoo_orders(self, cr, uid, job, context=None):
	""" See if order status is changed in Magento. If so then update it in Odoo
	"""
        storeview_obj = self.pool.get('mage.store.view')
        store_ids = storeview_obj.search(cr, uid, [('do_not_import', '=', False)])
        mappinglines = self._get_mappinglines(cr, uid, job.mapping.id)
        instance = job.mage_instance
	picking_obj = self.pool.get('stock.picking')
	#Get a list of all orders updated in the last 24 hours
	from_date = (datetime.utcnow() - timedelta(days=2)).strftime('%Y-%m-%d')
	sale_obj = self.pool.get('sale.order')
	picking_obj = self.pool.get('stock.picking')
	for storeview in storeview_obj.browse(cr, uid, store_ids):
            filters = {
                'store_id': {'=':storeview.external_id},
                'updated_at': {'gteq': {'from':from_date}},
		'created_at': {'gteq': {'from': '2016-03-01'}}
            }

	    #Get list of IDS
	    order_data = self._get_job_data(cr, uid, job, 'sales_order.search', [filters])
	    if not order_data:
		continue

	    #For each order in the response of orders updated
	    for order in order_data:
		increment_id = order['increment_id']
#		print 'INCREMENT', increment_id

		#Check Magento Status
		status = order.get('status')
		if not status:
		    continue

		#Find sales in Odoo that match the given id
		#an improvement would be to search with also status to reduce loading records
		sale_ids = sale_obj.search(cr, uid, [('mage_order_number', '=', increment_id)])
                if not sale_ids:
                    continue
		sale = sale_obj.browse(cr, uid, sale_ids[0])
		    #If the status in Odoo is not the same as Magento
		    if status == 'Amazon_New':
			sale.amazon_process == True

		    #if sale.mage_custom_status in ['new', 'pending']:

		    #RULE 1 - If the status on the sale is not the sale cascade immediately to the pickings for update in SW
		    if sale.mage_custom_status != status and status != 'o_complete':
			sale.mage_custom_status = status
			picking_ids = picking_obj.search(cr, uid, [('sale', '=', sale.id), ('state', '!=', 'done')])
			if picking_ids:
			    picking_obj.write(cr, uid, picking_ids, {'sw_exp': False})

		    #RULE 2 - If the order is pending then unreserve any reserved inventory
#		    if status in ['new', 'pending']:
#			picking_ids = picking_obj.search(cr, uid, [('sale', '=', sale.id), ('state', 'in', ['assigned', 'partially_available', 'confirmed'])])
 #			if picking_ids:
#			    sale.state = 'manual'
#			    for picking in picking_obj.browse(cr, uid, picking_ids):
#				if picking.state in ['partially_available', 'assigned']:
#				    picking_obj.do_unreserve(cr, uid, picking.id)
#
 #       			picking_obj.action_cancel(cr, uid, picking.id)
  #      			picking.reset_picking_draft()
   #     			procurement_obj = self.pool.get('procurement.order')
    #    			procurement_ids = procurement_obj.search(cr, uid, [('group_id', '=', picking.group_id.id)])
     #   			if procurement_ids:
      #      			    procurement_obj.write(cr, uid, procurement_ids, {'state': 'confirmed'})
#
#				picking_obj.write(cr, uid, [picking.id], {'sw_exp': False})
#

		    #RULE 3 - If the order is canceled in Magento cancel the order in Odoo and the pickings. The pickings must update
			#and not delete so shipworks is notified

		    if status == 'canceled' and sale.state != 'cancel':
			self.cancel_one_order(cr, uid, job, sale, False)


		    #RULE 4 - If the order is complete in Magento but is not detected as shipped in Odoo
		    if status == 'complete' and not sale.shipped:
			print sale.name
			if sale.state == 'draft':
			    self.confirm_one_order(cr, uid, sale)
			for picking in sale.picking_ids:
			    if picking.state == 'done':
				continue
                            if picking.state == 'draft':
                                picking_obj.action_confirm(cr, uid, [picking.id], context=context)
			    if picking.state != 'assigned':
            		        picking_obj.force_assign(cr, uid, [picking.id])
            		    picking.do_transfer()
			    picking_obj.write(cr, uid, [picking.id], {'sw_exp': False})

