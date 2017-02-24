from openerp.osv import osv, fields


class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'

    def fix_holded_pending(self, cr, uid, ids, context=None):
	picking_obj = self.pool.get('stock.picking')
	sale_obj = self.pool.get('sale.order')

	sale_ids = sale_obj.search(cr, uid, [('mage_custom_status', 'in', ['pending'])])
	for sale in sale_obj.browse(cr, uid, sale_ids):
	    print 'SALE REVERT', sale.name
	    for picking in sale.picking_ids:
		if picking.state in ['partially_available', 'confirmed', 'assigned']:
		    picking_obj.action_cancel(cr, uid, [picking.id])
		    picking.action_back_to_draft()
	    cr.commit()


    def check_order_status(self, cr, uid, job, context=None):
        import csv
	sale_obj = self.pool.get('sale.order')
	stock_obj = self.pool.get('stock.picking')

        input = open('/usr/local/openerp/community/mage2odoo/jobs/orders.csv', 'r')
        reader = csv.DictReader(input, quotechar='"', delimiter=',')
        for line in reader:
	    status = line['status']
	    order_no = line['increment_id']
	    order_ids = sale_obj.search(cr, uid, [('mage_order_number', '=', order_no)])
	    if not order_ids:
		print 'ORDER NOT FOUND', order_no
		continue

	    print 'ORDER', order_no
	    sale = sale_obj.browse(cr, uid, order_ids[0])
#	    stat = sale.mage_custom_status
	    self.mage_status_complete(cr, uid, sale)
#	    if stat != status:
#		sale.mage_custom_status = status

#	    if status not in ['pending', 'canceled', 'closed']:
#	    if status != 'o_complete':
#		continue
#	    cr.commit()
	    continue

#	    cancel = False
#	    print 'SALE', sale.name
#	    for picking in sale.picking_ids:
#		if picking.state in ['cancel', 'draft']:
#		    stock_obj.action_confirm(cr, uid, [picking.id], context=context)
#
#		if picking.state == 'done':
#		    stock_obj.action_revert_done(cr, uid, [picking.id])
#		    stock_obj.action_cancel(cr, uid, [picking.id])

#		elif picking.state != 'draft':
#		    picking.action_back_to_draft()
 
#		if status in ['canceled', 'closed']:
#		    cancel = True
#		    stock_obj.action_cancel(cr, uid, [picking.id])
#
#	    if cancel:
#		try:
#		    sale_obj.action_cancel(cr, uid, [sale.id])
##		except Exception, e:
#		    print e

#	    cr.commit()
