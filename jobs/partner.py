from openerp.osv import osv, fields
from pprint import pprint as pp
from datetime import datetime
from tzlocal import get_localzone

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'


    def import_updated_partners(self, cr, uid, job, context=None):
	instance = job.mage_instance
	filters = {}
	if instance.last_imported_customer:
	    filters = {'entity_id': {'gt': instance.last_imported_customer}}


        tz = get_localzone()
        now = datetime.utcnow()
        dt = tz.localize(now)
        string = dt.strftime('%Y-%m-%d')
        updated = {'updated_at': {'gteq': string}}
	filters.update(updated)

        partner_ids = self._get_job_data(cr, uid, job, 'oo_customer.search', [filters])

	if not partner_ids:
	    return True

	return self.import_partners(cr, uid, job, partner_ids)


    def import_all_partners(self, cr, uid, job, context=None):
        instance = job.mage_instance
        filters = False
        if instance.last_imported_customer:
            filters = {'entity_id': {'gt': instance.last_imported_customer}}

        partner_ids = self._get_job_data(cr, uid, job, 'oo_customer.search', [filters])

        if not partner_ids:
            return True

        return self.import_partners(cr, uid, job, partner_ids)


    def import_partners(self, cr, uid, job, partner_ids, context=None):
        datas = [partner_ids[i:i+900] for i in range(0, len(partner_ids), 900)]
 #       mappinglines = self._get_mappinglines(cr, uid, job.mapping.id)
	instance = job.mage_instance
	use_company = instance.use_partner_company
	mappinglines = False
        for data in datas:
            records = self._get_job_data(cr, uid, job, 'oo_customer.multinfo', [data])
            self.process_mage_partner_response(cr, uid, job, use_company, mappinglines, records)
            cr.commit()

        return True


    def process_mage_partner_response(self, cr, uid, job, use_company, mappinglines, records):
        partner_obj = self.pool.get('res.partner')
	for record in records:
	    try:
	        partner = partner_obj.get_or_create_customer(cr, uid, use_company, record)
		print 'Successfully synced Customer with Id %s' % record['entity_id']

	        if record['addresses']:
		    for address in record['addresses']:
		        partner_obj.get_or_create_partner_address(cr, uid, address, partner, address_type=False)
                        print 'Synced Customer Address'
	    except Exception, e:
		print e
	return True
