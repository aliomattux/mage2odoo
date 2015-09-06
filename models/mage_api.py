from openerp.osv import osv, fields
from openerp.tools.translate import _
from pprint import pprint as pp
from magento import API
import socket
import xmlrpclib

#class MageLog(osv.osv):
#    _name = 'mage.log'
#    _columns = {
#	'name': fields.char('Magento ID'),
#	'job': fields.many2one('mage.job', 'Job Failed on'),
#	'except_msg': fields.text('Exception Reason'),
#	'datetime': fields.datetime('Date Exception Occurred'),
#    }


class MageIntegrator(osv.osv):
    _name = 'mage.integrator'

    def get_external_credentials(self):
	mage_obj = self.pool.get('mage.setup')
	setup_ids = mage_obj.search(cr, uid, [], limit=1)
	if setup_ids:
	    instance = setup_ids.browse(cr, uid, setup_ids[0])
	    return {
		'url': instance.url,
		'username': instance.username,
		'password': instance.password,
	    }
	else:
	    raise osv.except_osv(_('Config Error'), _('You must have already configured Magento to run this function!'))
	    

    def _get_credentials(self, job):
        return {
                'url': job.mage_instance.url,
                'username': job.mage_instance.username,
                'password': job.mage_instance.password,
        }


    def _get_job_data(self, cr, uid, job, method, arguments):
        credentials = self._get_credentials(job)
	return self._mage_call(credentials, method, arguments)


    #This method copied from magentoerpconnect for v7
    def _mage_call(self, credentials, method, arguments):
        try:
            with API(credentials['url'],
                                credentials['username'],
                                credentials['password']) as mage_api:
                return mage_api.call(method, arguments)

        except (socket.gaierror, socket.error, socket.timeout) as err:
	    raise osv.except_osv(_('Network/URL Config Error'), _('Either you entered the URL in wrong or you have no internet connectivity'))
        except xmlrpclib.ProtocolError as err:
            if err.errcode in [502,   # Bad gateway
                               503,   # Service unavailable
                               504]:  # Gateway timeout
		raise osv.except_osv(_('Connection Error'), _('Server Returned Error Code: %s')%err.errcode)
            else:
		raise osv.except_osv(_('Generic Connection Error'), _("Could Not Authenticate/Connect with Magento!\n" \
			"Please verify that\n1. The Magento module is installed in the LOCAL folder on Magento.\n" \
			"2. Your webservice user in Magento is setup with FULL Admin access.\n" \
			"3. Verify your Odoo server can reach Magento.\n" \
			"4. Verify that you have entered the correct Credentials"))

	except Exception, e:
	    raise osv.except_osv(_('Magento Returned an Error'), _('%s')%e)


    def _get_product_type_selections(self, cr, uid, job, conversion_type, \
		mappingline, record):

	type_obj = self.pool.get('mage.product.type')
	print mappingline
	print record
#	attribute_obj = self.pool.get('product.attribute')
#	assigned_types = field_value.split(',')
#	for type in assigned_types:
#	    type_id = type_obj.search(cr, uid, [('type', '=', type)])
#	    attribute_obj.write(cr, uid, 
	return {}


    def _get_attribute_type_conversion(self, cr, uid, job, conversion_type, \
		mappingline, record):

	attribute_obj = self.pool.get('product.attribute')
	transform_dict = attribute_obj._frontend_options()
	pp(record)
	return {'ttype': transform_dict[record[mappingline['mage_fieldname']]]}
