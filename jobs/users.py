from openerp.osv import osv, fields
from pprint import pprint as pp
from datetime import datetime
from tzlocal import get_localzone

class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'

    def sync_admin_users(self, cr, uid, job, context=None):
	user_obj = self.pool.get('res.users')
        records = self._get_job_data(cr, uid, job, 'oo_websites.users', [])
	pp(records)
	for record in records:
	    vals = self.prepare_user_vals(cr, uid, record)
	    user_ids = user_obj.search(cr, uid, [('login', '=', record['email'])])
	    if user_ids:
		user_obj.write(cr, uid, user_ids[0], vals)
		print 'Updated User with ID: %s' % vals['external_id']
	    else:
		user_obj.create(cr, uid, vals)
		print 'Created User in Odoo with ID: %s' % vals['external_id']

        return True


    def prepare_user_vals(self, cr, uid, record):
	vals = {
		'login': record['email'],
		'name': ' '.join([record['firstname'], record['lastname']]),
		'external_id': record['user_id']
	}

	return vals
