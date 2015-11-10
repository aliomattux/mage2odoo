from openerp.osv import osv, fields
from pprint import pprint as pp
from datetime import datetime
from tzlocal import get_localzone

class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
	'tmp_price': fields.float('Temp Price'),
    }

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'

    def update_product_cost(self, cr, uid, job, context=None):
	
	product_obj = self.pool.get('product.product')
	product_ids = product_obj.search(cr, uid, [])
	for product in product_obj.browse(cr, uid, product_ids):
	    price = product.standard_price
	    product_obj.write(cr, uid, product.id, {'tmp_price': price})
	    print 'Updated Price'


	cr.execute("UPDATE sale_order_line line SET purchase_price = product.tmp_price FROM product_product product WHERE product.id = line.product_id")
	cr.commit()
