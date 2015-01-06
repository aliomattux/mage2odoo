from openerp.osv import osv, fields

class AccountInvoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
	'mage_export_error': fields.boolean('Magento Export Error', copy=False),
	'external_id': fields.integer('Magento Invoice ID', copy=False, select=True),
    }
