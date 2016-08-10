from openerp.osv import osv, fields


class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'


    def fix_assigned_shipments(self, cr, uid, job, context=None):
	query = "SELECT DISTINCT id AS picking_id FROM stock_picking WHERE sale IN (SELECT id FROM sale_order WHERE mage_custom_status in ('new', 'pending'))"
	cr.execute(query)
	picking_obj = self.pool.get('stock.picking')
	results = cr.dictfetchall()
	for rec in results:
	    picking_id = rec['picking_id']
	    picking = picking_obj.browse(cr, uid, picking_id)
            if picking.state == 'done':
		print 'PICKING DONE', picking.id
                continue

            if picking.state in ['partially_available', 'assigned']:
                picking_obj.do_unreserve(cr, uid, picking.id)

            picking_obj.action_cancel(cr, uid, picking.id)
            picking.reset_picking_draft()
            procurement_obj = self.pool.get('procurement.order')
            procurement_ids = procurement_obj.search(cr, uid, [('group_id', '=', picking.group_id.id)])
            if procurement_ids:
                procurement_obj.write(cr, uid, procurement_ids, {'state': 'confirmed'})
