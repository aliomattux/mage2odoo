from openerp.osv import osv, fields
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
	    print 'Network Error'
#            raise NetworkRetryableError(
 #               'A network error caused the failure of the job: '
  #              '%s' % err)
        except xmlrpclib.ProtocolError as err:
            if err.errcode in [502,   # Bad gateway
                               503,   # Service unavailable
                               504]:  # Gateway timeout
	        print 'Other Error'
#                raise RetryableJobError(
 #                   'A protocol error caused the failure of the job:\n'
  #                  'URL: %s\n'
   #                 'HTTP/HTTPS headers: %s\n'
    #                'Error code: %d\n'
     #               'Error message: %s\n' %
      #              (err.url, err.headers, err.errcode, err.errmsg))
            else:
                raise


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
