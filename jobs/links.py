from openerp.osv import osv, fields
from pprint import pprint as pp
from datetime import datetime
from tzlocal import get_localzone

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'

    def test_attribute_options(self, cr, uid, job, context=None):
        records = self._get_job_data(cr, uid, job, 'sales_order.shipping_methods', [])

	return True


    def import_product_links(self, cr, uid, job, context=None):
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
                self.process_mage_product_links_response(cr, uid, job, mappinglines, records)
#                cr.commit()
            except Exception, e:
                print e

        return True


    def process_mage_product_links_response(self, cr, uid, job, mappinglines, records):
#        target_obj = self.pool.get(job.mapping.model_id.model)
	product_obj = self.pool.get('product.product')

        for record in records:
#	    pp(record)
	    related_data = []
	    #Solves bug with null sku
	    if not record['sku']:
		continue
	    if record['sku'] == 'sbls12-12':
		raise

	    print 'SKU', record['sku']
	    product = product_obj.get_or_create_odoo_record(cr, uid, job, record['entity_id'], False)
	    if record.get('related'):
		cr.execute('DELETE FROM product_link WHERE product_tmpl_id = %s'%product.product_tmpl_id.id)
		for related in record.get('related'):
		    vals = {
			'linked_product': product_obj.get_or_create_odoo_record(cr, uid, job, related['product_id'], False),
			'product_tmpl_id': product.product_tmpl_id.id,
			'linked_type': 'related',
			'position': related['position'],
		    }
		    related_data.append((0, 0, vals))

#		pp(related_data)
		product.product_links = related_data
		cr.commit()
        return True


