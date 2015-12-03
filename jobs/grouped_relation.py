from openerp.osv import osv, fields
from pprint import pprint as pp
from datetime import datetime
from tzlocal import get_localzone

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'

    def test_attribute_options(self, cr, uid, job, context=None):
        records = self._get_job_data(cr, uid, job, 'sales_order.shipping_methods', [])

	return True


    def import_grouped_product_relation(self, cr, uid, job, context=None):
	product_obj = self.pool.get('product.product')

	product_ids = product_obj.search(cr, uid, ['|',('external_id', '!=', False), ('external_id', '!=', 0)])
	product_data = product_obj.read(cr, uid, product_ids, fields=['external_id'])
	external_ids = [x['external_id'] for x in product_data]
	print 'IDS', len(external_ids) 
        datas = [external_ids[i:i+900] for i in range(0, len(external_ids), 900)]
        mappinglines = self._get_mappinglines(cr, uid, job.mapping.id)

        for data in datas:
            try:
                records = self._get_job_data(cr, uid, job, 'oo_catalog_product.multinfo', [data, True])
                self.process_mage_grouped_products_response(cr, uid, job, mappinglines, records)
#                cr.commit()
            except Exception, e:
                print e

        return True


    def process_mage_grouped_products_response(self, cr, uid, job, mappinglines, records):
#        target_obj = self.pool.get(job.mapping.model_id.model)
	product_obj = self.pool.get('product.product')

        for record in records:
#	    pp(record)
	    grouped_data = []
	    #Solves bug with null sku
	    if not record['sku']:
		continue
	    pp(record['sku'])

	    product = product_obj.get_or_create_odoo_record(cr, uid, job, record['entity_id'], False)
	    if record.get('grouped'):
		cr.execute('DELETE FROM mage_grouped_product WHERE product_tmpl_id = %s'%product.product_tmpl_id.id)
		for grouped_item in record.get('grouped'):
		    vals = {
			'product': product_obj.get_or_create_odoo_record(cr, uid, job, grouped_item['product_id'], False),
			'product_tmpl_id': product.product_tmpl_id.id,
			'qty': grouped_item['qty'],
			'position': grouped_item['position'],
		    }
		    grouped_data.append((0, 0, vals))

		pp(grouped_data)
		product.grouped_products = grouped_data
		cr.commit()
        return True


