from openerp.osv import osv, fields
from pprint import pprint as pp
from magento import API
from openerp.tools.translate import _
from datetime import datetime, timedelta

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'

    def mage_core_sync_stock(self, cr, uid, job):
	instance = job.mage_instance

        integrator_obj = self.pool.get('mage.integrator')
        credentials = integrator_obj.get_external_credentials(cr, uid)
	if not instance.sync_policy:
	    #TODO: Raise error or something
	    return True

	if instance.sync_policy == 'all':
	    return self.synchronize_all_magento_stock(cr, uid, job)

	last_sync_date = instance.last_inventory_sync_date
	print 'Last Sync Date', last_sync_date
	if not last_sync_date:
	    last_sync_date = datetime.utcnow() - timedelta(days=1)

	move_query = "SELECT DISTINCT product_id" + \
		" FROM stock_move" + \
		" WHERE state NOT IN ('draft', 'cancel')" + \
		" AND create_date > '%s'" % last_sync_date

	cr.execute(move_query)
	move_data = cr.dictfetchall()
	instance.last_sync_date = datetime.utcnow()
#	move_ids = [d['product_id'] for d in move_data]
	move_ids = [44655]
	if not move_ids:
	    print 'No Move Data'
	    return
	bom_query = "SELECT product.id" + \
		" FROM mrp_bom_line line" + \
		" JOIN mrp_bom bom ON (line.bom_id = bom.id)" + \
		" JOIN product_product product ON (bom.product_tmpl_id = product.product_tmpl_id)" + \
		" WHERE line.product_id IN (%s)" % str(move_ids).replace('[', '').replace(']', '')
	cr.execute(bom_query)
	bom_data = cr.dictfetchall()
	if bom_data:
	    bom_ids = [b['id'] for b in bom_data]
            move_ids.extend(bom_ids)
	print 'Move IDS', move_ids
	return self.sync_mage_stock_product_ids(cr, uid, credentials, move_ids)


    def synchronize_all_magento_stock(self, cr, uid, job):
        integrator_obj = self.pool.get('mage.integrator')
        credentials = integrator_obj.get_external_credentials(cr, uid)

	product_obj = self.pool.get('product.product')
	product_ids = product_obj.search(cr, uid, [('sync_stock', '=', True), ('sync_to_mage', '=', True)])
	return self.sync_mage_stock_product_ids(cr, uid, product_ids)


    def sync_mage_stock_product_ids(self, cr, uid, credentials, product_ids):
	product_data = {}
	product_obj = self.pool.get('product.product')
	for product in product_obj.browse(cr, uid, product_ids):

	    print product.name
	    if not product.external_id or product.external_id < 1:
		print 'Skipping'
		continue
	    qty = product.immediately_usable_qty
	    always_in_stock = product.always_in_stock
	    manage_stock = product.manage_stock
	    use_config = product.use_config_manage_stock
	    if always_in_stock:
		is_in_stock = 1
	    elif qty > 1:
		is_in_stock = 1
	    else:
		is_in_stock = 0

	    product_data[str(product.external_id)] = {
		'is_in_stock': is_in_stock,
		'qty': int(qty),
		'manage_stock': 1 if manage_stock else 0,
		'config_manage_stock': 1 if use_config else 0,
	    }

	print 'HERE'
	return self.push_magento_product_stock(cr, uid, credentials, product_data)


    def push_magento_product_stock(self, cr, uid, credentials, product_data):
	print 'CALLING FUNCTION'
	try:
	    pp(product_data)
	    with API(credentials['url'], credentials['username'], credentials['password']) as product_api:
		results = product_api.call('oo_catalog_product.updateproductstock', [product_data])
		print 'Results', results
	except Exception, e:
	    raise osv.except_osv(_('Magento API Error!'),_(str(e)))

        return True
