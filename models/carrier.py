from openerp.osv import osv, fields


class DeliveryCarrier(osv.osv):
    _inherit = 'delivery.carrier'
    _columns = {
	'mage_code': fields.char('Magento ID'),
    }
