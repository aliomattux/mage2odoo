from openerp.osv import osv, fields
from pprint import pprint as pp
from magento import API
from openerp.tools.translate import _


class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
	'tmp_price': fields.float('Temp Price'),
    }

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'

    def synchronize_magento_stock(self, cr, uid, job):
        integrator_obj = self.pool.get('mage.integrator')
        credentials = integrator_obj.get_external_credentials(cr, uid)

	product_obj = self.pool.get('product.product')
	product_ids = product_obj.search(cr, uid, [('sync_stock', '=', True), ('sync_to_mage', '=', True)])
#	product_ids = [2389]
	product_data = {}
	for product in product_obj.browse(cr, uid, product_ids):
	    if not product.external_id or product.external_id < 1:
		continue
	    qty = product.qty_available
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

	try:
	    pp(product_data)
	    with API(credentials['url'], credentials['username'], credentials['password']) as product_api:
		results = product_api.call('oo_catalog_product.updateproductstock', [product_data])
		print 'Results', results
	except Exception, e:
	    raise osv.except_osv(_('Magento API Error!'),_(str(e)))

        return True
