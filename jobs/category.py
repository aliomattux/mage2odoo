from openerp.osv import osv, fields
from pprint import pprint as pp

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'

    def import_categories(self, cr, uid, job, context=None):
	categories = self._get_job_data(cr, uid, job, 'catalog_category.tree', [])
	cat_obj = self.pool.get('product.category')
	mappinglines = self._get_mappinglines(cr, uid, job.mapping.id)
	vals = cat_obj.prepare_odoo_record_vals(cr, uid, job, categories)
#	vals = self._transform_record(cr, uid, job, categories, 'from_mage_to_odoo', mappinglines)
	del vals['parent_id']
	result = cat_obj.upsert_mage_record(cr, uid, vals)
	print result
	self.process_category_tree(cr, uid, job, mappinglines, categories['children'])

	return True


    def process_category_tree(self, cr, uid, job, mappinglines, categories, context=None):
	cat_obj = self.pool.get('product.category')
	for category in categories:
	    vals = cat_obj.prepare_odoo_record_vals(cr, uid, job, category)
	    result = cat_obj.upsert_mage_record(cr, uid, vals)
	    print result
	    if category['children']:
		self.process_category_tree(cr, uid, job, mappinglines, category['children'])

	return True

