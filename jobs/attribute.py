from openerp.osv import osv, fields
from pprint import pprint as pp


class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'


    def sync_mage_attribute_data(self, cr, uid, job, context=None):
	self.import_attribute_sets(cr, uid, job)
	self.import_attribute_groups(cr, uid, job)
	self.import_attributes(cr, uid, job)
	self.import_attribute_values(cr, uid, job)
	self.import_attribute_groups_attribute_relation(cr, uid, job)
	return True


    def import_attribute_sets(self, cr, uid, job, context=None):
	set_obj = self.pool.get('product.attribute.set')
	records = self._get_job_data(cr, uid, job, 'catalog_product_attribute_set.list', [])
	for record in records:
	    vals = set_obj.prepare_odoo_record_vals(cr, uid, job, record)
	    result = set_obj.upsert_mage_record(cr, uid, vals)
	    print result

	return True


    def import_attribute_groups(self, cr, uid, job, context=None):
	set_obj = self.pool.get('product.attribute.set')
	group_obj = self.pool.get('product.attribute.group')
	set_ids = set_obj.search(cr, uid, [])
	set_data = set_obj.read(cr, uid, set_ids, fields=['external_id'])
	sets = [x['external_id'] for x in set_data]
	records = self._get_job_data(cr, uid, job, 'ol_catalog_product_attribute_group.list', \
		[{'attribute_set_id': {'in': sets}}])

	for record in records:
	    vals = group_obj.prepare_odoo_record_vals(cr, uid, job, record)
	    result = group_obj.upsert_mage_record(cr, uid, vals)
	    print result

	return True
	    	    

    def import_attributes(self, cr, uid, job, context=None):
	attribute_obj = self.pool.get('product.attribute')
        records = self._get_job_data(cr, uid, job, 'ol_catalog_product_attribute.list', [])
	for record in records:
            if record.get('is_visible') == '0':
                continue
	    vals = attribute_obj.prepare_odoo_record_vals(cr, uid, job, record)
	    result = attribute_obj.upsert_mage_record(cr, uid, vals)

	return True
	

    def import_attribute_values(self, cr, uid, job, context=None):
       attr_obj = self.pool.get('product.attribute')
       value_obj = self.pool.get('product.attribute.value')
       attr_ids = attr_obj.search(cr, uid, [('is_user_defined', '=', True)])
       attr_data = attr_obj.read(cr, uid, attr_ids, fields=['external_id'])
       attributes = [x['external_id'] for x in attr_data]
       for attribute in attributes:
            records = self._get_job_data(cr, uid, job, 'ol_catalog_product_attribute.options', [attribute])
	    for record in records:
		vals = value_obj.prepare_odoo_record_vals(cr, uid, job, record)
		value_obj.upsert_mage_record(cr, uid, vals)

       return True


    def process_mage_attribute_response(self, cr, uid, job, mappinglines, records):
	target_obj = self.pool.get(job.mapping.model_id.model)

	for record in records:
	    #This needs to be fixed on Magento
	    if record.get('is_visible') == '0':
		continue
		
        return True


    def find_attribute_group_relationship(self, cr, uid, attr_data):
	result = {}
	attr_obj = self.pool.get('product.attribute')
	group_obj = self.pool.get('product.attribute.group')
	attr_ids = attr_obj.search(cr, uid, [('external_id', '=', attr_data['attribute_id'])])
	#This needs to be fixed in Magento
	if not attr_ids:
	    return False
	result['attribute'] = attr_ids[0]
	group_ids = group_obj.search(cr, uid, [('external_id', '=', attr_data['group_id'])])
	result['group'] = group_ids[0]
	return result


    def import_attribute_groups_attribute_relation(self, cr, uid, job, context=None):
        set_obj = self.pool.get('product.attribute.set')
        set_ids = set_obj.search(cr, uid, [])
        set_data = set_obj.read(cr, uid, set_ids, fields=['external_id'])
        sets = [x['external_id'] for x in set_data]
	group_obj = self.pool.get('product.attribute.group')
	buffer = {}
	for set in sets:
            records = self._get_job_data(cr, uid, job, 'ol_catalog_product_attribute.relations', [set])
	    count = 0
	    for record in records:
		if not record['attribute_id']:
		    count += 1
		    continue
		#This needs to be fixed in Magento
		dic = self.find_attribute_group_relationship(cr, uid, record)
		if not dic:
		    continue
		if dic['group'] not in buffer.keys():
		    buffer[dic['group']] = [dic['attribute']]
		else:
		    buffer[dic['group']].append(dic['attribute'])

	    for k, v in buffer.items():
	        group_obj.write(cr, uid, k, 
	        {'attributes': [(6, 0, v)]})

	return True
