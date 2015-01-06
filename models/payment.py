from openerp.osv import osv, fields


class PaymentMethod(osv.osv):
    _inherit = 'payment.method'
    _columns = {
	'mage_code': fields.char('Magento Code', select=True),

    }
