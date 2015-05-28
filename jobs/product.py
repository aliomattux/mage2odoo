from openerp.osv import osv, fields
from pprint import pprint as pp
from datetime import datetime
from tzlocal import get_localzone

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


    def get_product_job_call(self, cr, uid, job, context=None):
	call = 'oo_catalog_product.allsqlsearch'

	return call


    def get_update_filters(self, job):
	status_filter = self.get_status_filter(job)
	filters = status_filter
	#YYYY-MM-DD
	tz = get_localzone()
	now = datetime.utcnow()
	dt = tz.localize(now)
	string = dt.strftime('%Y-%m-%d')
	updated = {'updated_at': {'gteq': string}}
	filters.update(updated)

        return [filters]


    def get_status_filter(self, job):
        statuses = ['1']
        if job.mage_instance.import_disabled_products:
            statuses.append('2')
	return {'status': {'in': statuses}}


    def get_all_filters(self, job):
	status_filter = self.get_status_filter(job)
	filters = status_filter
        return [filters]


    def get_updated_api_call(self):
	return 'oo_catalog_product.filtersearch'


    def get_all_api_call(self):
	return 'oo_catalog_product.filtersearch'


    def import_updated_products(self, cr, uid, job, context=None):
	call = self.get_updated_api_call()
	filters = self.get_update_filters(job)
	product_ids = self._get_job_data(cr, uid, job, call, filters)
	return self.import_products(cr, uid, job, product_ids)


    def import_all_products(self, cr, uid, job, context=None):
	call = self.get_all_api_call()
	filters = self.get_all_filters(job)
	product_ids = self._get_job_data(cr, uid, job, call, filters)
	return self.import_products(cr, uid, job, product_ids)


    def import_products(self, cr, uid, job, product_ids, context=None):
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


