from openerp.osv import osv, fields


class MageImportException(osv.osv):
    _name = 'mage.import.exception'
    _rec_name = 'external_id'
    _columns = {
	'type': fields.char('Type'),
	'external_id': fields.char('External Id'),
	'message': fields.text('Message'),
	'data': fields.text('Data'),
	'job': fields.many2one('external.job', 'Job'),
    }

    def retry_job_object(self, cr, uid, ids):
	return True
    
