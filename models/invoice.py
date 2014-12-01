from openerp.osv import osv, fields

class AccountInvoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
	'mage_export_error': fields.boolean('Magento Export Error'),
	'external_id': fields.integer('Magento Invoice ID'),
    }
