from openerp.osv import osv, fields


class MageExportException(osv.osv):
    _name = 'mage.export.exception'
    _columns = {
	'name': fields.char('Name'),
	'type': fields.char('Type'),
	'external_id': fields.char('External Id'),
	'message': fields.text('Message'),
	'data': fields.text('Data'),
	'job': fields.many2one('mage.job', 'Job'),
    }

    def retry_job_object(self, cr, uid, ids):
	return True
    
