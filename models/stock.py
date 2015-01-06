from openerp.osv import osv, fields

class StockPicking(osv.osv):
    _inherit = 'stock.picking'
    _columns = {
	'mage_export_error': fields.boolean('Magento Export Error', copy=False),
	'external_id': fields.integer('Magento Shipment ID', copy=False, select=True),
        'sale': fields.many2one('sale.order', 'Sale Order', select=True),
        'shipping_state': fields.related('partner_id', 'state_id', type='many2one', relation='res.country.state', string='Shipping State'),
        'shipping_city': fields.related('partner_id', 'city', type='char', string='Shipping City'),
        'mage_store': fields.related('sale', 'mage_store', type='many2one', relation='mage.store.view', string='Magento Store'),
    }
