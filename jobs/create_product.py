from openerp.osv import osv, fields
from pprint import pprint as pp
from magento import API
from datetime import datetime
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class MageIntegrator(osv.osv):
    _inherit = 'mage.integrator'

    def create_mage_products(self, cr, uid, job):
        
	query = " SELECT product.id FROM product_product product" + \
		" JOIN product_template template ON (product.product_tmpl_id = template.id)" + \
		" WHERE template.sync_to_mage = True" + \
		" AND external_id = 0 OR external_id IS NULL" \
		" AND product.default_code IS NOT NULL" \
		" AND mage_last_sync_date IS NULL"
#		" AND template.write_date AT TIME ZONE 'UTC' > mage_last_sync_date AT TIME ZONE 'UTC' IS NULL"
	cr.execute(query)
	product_data = cr.dictfetchall()
	product_ids = [p['id'] for p in product_data]

	print 'Product IDS', product_ids

	credentials = self.get_external_credentials(cr, uid)
	product_obj = self.pool.get('product.product')
	for product in product_obj.browse(cr, uid, product_ids):
	    shell_data = self.prepare_shell_product(cr, uid, product)
	    storeview = False
	    result = self.upsert_shell_product(cr, uid, credentials, \
		shell_data, product, storeview
	    )
	return True


    def prepare_shell_product(self, cr, uid, product):
	#visibility - 1 not visible individually
	#2 Catalog
	#3 search
	#4 Catalog, Search

	#Tax Class - 0 None
	#2 Taxable Goods
	#4 Shipping
	#7 EOD Taxable Products

	#status 1 Enabled
	#2 Disabled

#	cat_ids = [cat.external_id for cat in product.categ_ids]
	cat_ids = []
	web_ids = [web.external_id for web in product.websites]

	vals = {
		'name': product.name,
		'description': product.description,
		'short_description': product.short_description,
		'weight': product.weight,
		'status': 2,
		'url_key': product.url_key or None,
#		'url_path':
		'visibility': 1,
		'category_ids': cat_ids,
		'website_ids': web_ids,
		'price': 86753.09,
		'tax_class_id': product.mage_tax_class.external_id,
	}
	

	return vals


    def upsert_shell_product(self, cr, uid, credentials, shell_data, product, storeview):
        try:
            with API(credentials['url'], credentials['username'], credentials['password']) as product_api:
                external_id = product_api.call('oo_catalog_product.create', [product.mage_type, product.set.external_id, product.default_code, shell_data, storeview])
		self.pool.get('product.product').write(cr, uid, product.id, {'external_id': external_id, 'mage_last_sync_date': datetime.utcnow()})
        except Exception, e:
            raise osv.except_osv(_('Magento API Error!'),_(str(e)))
	    #TODO: Create Exception Object
        return True
