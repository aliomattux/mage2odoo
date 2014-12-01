from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
from pprint import pprint as pp

class MageJob(osv.osv):
    _name = 'mage.job'
    _columns = {
        'name': fields.char('Name', required=True),
	'core_job': fields.boolean('Core Job'),
	'mage_instance': fields.many2one('mage.setup', 'Magento Instance', required=True),
	'scheduler': fields.many2one('ir.cron', 'Scheduler', readonly=True),
	'mapping': fields.many2one('mage.mapping', 'Mapping'),
	'element_inspector': fields.text('Element Inspector'),
	'job_type': fields.selection([('direct_import', 'Direct Import'),
				      ('custom', 'Python Code'),
				      ('system', 'System')], 'Job Type', required=True),
	'threaded': fields.boolean('Threaded Job'),
	'python_model': fields.many2one('ir.model', 'Python Model'),
	'python_function_name': fields.char('Python Function Name'),
    }


    def button_execute_job(self, cr, uid, ids, context=None):
        job = self.browse(cr, uid, ids[0])
        result = self.import_resources(cr, uid, job)
#        if result and result != 'False':
 #           raise osv.except_osv(_("API Response Error!"), _(result))

        return True


    def import_resources(self, cr, uid, job, context=None):
        """
        """
	job_obj = self.pool.get(job.python_model.name)
        #If we are using a custom code implementation
        if job.job_type == 'direct_import':
            return getattr(job_obj, job.python_function_name)(cr, uid, job)

        elif job.job_type in ['custom', 'system']:
            return getattr(job_obj, job.python_function_name)(cr, uid, job)


	return False


    def button_schedule_mage_job(self, cr, uid, ids, context=None):
	for job in self.browse(cr, uid, ids):
	    if job.scheduler:
		continue
	    cron_id = self.create_mage_schedule(cr, uid, job.id, job.name)
	    self.write(cr, uid, job.id, {'scheduler': cron_id})
	return True


    def create_mage_schedule(self, cr, uid, job_id, job_name, context=False):
        vals = {'name': job_name,
                'active': False,
                'user_id': SUPERUSER_ID,
                'interval_number': 15,
                'interval_type': 'minutes',
                'numbercall': -1,
                'doall': False,
                'model': 'mage.job',
                'function': 'button_execute_job',
                'args': '([' + str(job_id) +'],)',
        }

        return self.pool.get('ir.cron').create(cr, uid, vals, context)
