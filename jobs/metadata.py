from openerp.osv import osv, fields
from pprint import pprint as pp

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'


    def sync_mage_metadata(self, cr, uid, job, context=None):
        self.import_websites(cr, uid, job)
        self.import_store_groups(cr, uid, job)
        self.import_store_views(cr, uid, job)
        self.sync_instance_carriers(cr, uid, job)
        self.sync_instance_order_statuses(cr, uid, job)
        return True


    def sync_instance_carriers(self, cr, uid, job, context=None):
        records = self._get_job_data(cr, uid, job, 'sales_order.shipping_methods', [])
        carrier_obj = self.pool.get('mage.mapping.carrier')

        for record in records:
            vals = {'mage_carrier_code': record['code'],
                    'name': record['label']
            }
            existing_ids = carrier_obj.search(cr, uid,
                [('mage_carrier_code', '=', record['code'])])

            if not existing_ids:
                result = carrier_obj.create(cr, uid, vals)
                print (True, result)
            else:
                print (False, existing_ids[0])

        return True


    def sync_instance_order_statuses(self, cr, uid, job, context=None):
        records = self._get_job_data(cr, uid, job, 'sales_order.get_order_states', [])
        mage_order_state_obj = self.pool.get('mage.mapping.order.state')
        for k, v in records.items():
            vals = {'mage_order_state': k,
                    'name': v
            }
            existing_ids = mage_order_state_obj.search(cr, uid,
                [('mage_order_state', '=', k)])

            if not existing_ids:
                result = mage_order_state_obj.create(cr, uid, vals)
                print (True, result)
            else:
                print (False, existing_ids[0])

        return True


    def import_websites(self, cr, uid, job, context=None):
	website_obj = self.pool.get('mage.website')
        records = self._get_job_data(cr, uid, job, 'ol_websites.list', [])
        for record in records:
            vals = website_obj.prepare_odoo_record_vals(cr, uid, job, record)
            result = website_obj.upsert_mage_record(cr, uid, vals)
            print result

        return True


    def import_store_groups(self, cr, uid, job, context=None):
	group_obj = self.pool.get('mage.store.group')
        records = self._get_job_data(cr, uid, job, 'ol_groups.list', [])
        for record in records:
            vals = group_obj.prepare_odoo_record_vals(cr, uid, job, record)
            result = group_obj.upsert_mage_record(cr, uid, vals)
            print result

        return True


    def import_store_views(self, cr, uid, job, context=None):
	storeview_obj = self.pool.get('mage.store.view')

        records = self._get_job_data(cr, uid, job, 'ol_storeviews.list', [])
	for record in records:
	    vals = storeview_obj.prepare_odoo_record_vals(cr, uid, job, record)
	    result = storeview_obj.upsert_mage_record(cr, uid, vals)
	    print result

	return True


#    def process_mage_websites_response(self, cr, uid, job, mappinglines, records):
#        target_obj = self.pool.get(job.mapping.model_id.model)

#        for record in records:
#            vals = self._transform_record(cr, uid, job, record, 'from_mage_to_odoo', mappinglines)
#            result = target_obj.upsert_mage_data(cr, uid, vals)
#        return True


