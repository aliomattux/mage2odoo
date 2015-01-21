from openerp.osv import osv, fields
from pprint import pprint as pp

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'

    def test_attribute_options(self, cr, uid, job, context=None):
        records = self._get_job_data(cr, uid, job, 'sales_order.shipping_methods', [])

	return True


    def import_configurable_links(self, cr, uid, job, context=None):
	product_obj = self.pool.get('product.product')

	product_ids = product_obj.search(cr, uid, [('mage_type', '=', 'configurable')])
	product_data = product_obj.read(cr, uid, product_ids, fields=['external_id'])
	external_ids = [x['external_id'] for x in product_data]
        records = self._get_job_data(cr, uid, job, 'oo_catalog_product.associatedproducts', [external_ids])

	#For each configurable, locate available child products
	for record in records:
	    vals = {'associated_products': [(5)]}
#	    product = get_or_create_product_
	    product_ids = product_obj.search(cr, uid, [('external_id', 'in', record['associated_products'])])
	    product_id = product_obj.get_or_create_odoo_record(cr, uid, job, record['entity_id']).id
	    if product_ids:
	        vals = {'associated_products': [(6, 0, product_ids)]}

	    result = product_obj.upsert_mage_record(cr, uid, vals, product_id)
	    print 'RESULT', result

	return True


    def import_products(self, cr, uid, job, context=None):
	#TODO: This needs to be broken up more, allow variables like start/stop id
	product_ids = self._get_job_data(cr, uid, job, 'oo_catalog_product.allsqlsearch', [])
	datas = [product_ids[i:i+900] for i in range(0, len(product_ids), 900)]
        mappinglines = self._get_mappinglines(cr, uid, job.mapping.id)

	for data in datas:
            records = self._get_job_data(cr, uid, job, 'oo_catalog_product.multinfo', [data])
            self.process_mage_products_response(cr, uid, job, mappinglines, records)
	    cr.commit()

	return True


    def process_mage_products_response(self, cr, uid, job, mappinglines, records):
#        target_obj = self.pool.get(job.mapping.model_id.model)
	product_obj = self.pool.get('product.product')
        for record in records:
	    try:
	        vals = product_obj.prepare_odoo_record_vals(cr, uid, job, record)
                vals.update(self._transform_record(cr, uid, job, record, \
			'from_mage_to_odoo', mappinglines))
                result = product_obj.upsert_mage_record(cr, uid, vals)
	    except Exception, e:
		continue

        return True


