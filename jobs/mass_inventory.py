from openerp.osv import fields, osv, orm
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp import tools

class MageJob(osv.osv):
    _inherit = "mage.job"

    def zero_all_negative(self, cr, uid, job, context=None):
        if context is None:
            context = {}

	location = 12
	location_name = 'Stock'

        inventory_obj = self.pool.get('stock.inventory')
        inventory_line_obj = self.pool.get('stock.inventory.line')
	product_obj = self.pool.get('product.product')

        filter = 'partial'
        inventory_id = inventory_obj.create(cr, uid, {
	    'name': 'Zero Inventory For Location: %s' % location_name,
            'filter': filter,
            'location_id': location,
	}, context=context)

	product_ids = product_obj.search(cr, uid, [])
	ok = False
        for product in product_obj.browse(cr, uid, product_ids, context={'location_id': location, 'location': location}):
	    product_qty_available = product.qty_available
	    if product_qty_available < 0:
		ok = True
	        print 'SKU: %s' % product.default_code
	        print 'Quantity Available: %s' % product.qty_available

                product = product.with_context(location=location, lot_id=False)
                th_qty = product.qty_available
                line_data = {
                    'inventory_id': inventory_id,
                    'product_qty': 0,
                    'location_id': location,
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                    'theoretical_qty': th_qty,
                    'prod_lot_id': False
                }
                inventory_line_obj.create(cr , uid, line_data, context=context)

#	if ok:
#            inventory_obj.action_done(cr, uid, [inventory_id], context=context)
        return True
