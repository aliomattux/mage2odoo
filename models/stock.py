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


    def reset_to_draft(self, cr, uid, ids, context=None):
	picking = self.browse(cr, uid, ids[0])
	return self.picking_reset_to_draft(cr, uid, picking)

    def picking_reset_to_draft(self, cr, uid, picking, context=None):
        if picking.state in ['partially_available', 'assigned']:
            self.do_unreserve(cr, uid, picking.id)

        self.action_cancel(cr, uid, picking.id)
        picking.reset_picking_draft()
        procurement_obj = self.pool.get('procurement.order')
        procurement_ids = procurement_obj.search(cr, uid, [('group_id', '=', picking.group_id.id)])
        if procurement_ids:
            procurement_obj.write(cr, uid, procurement_ids, {'state': 'confirmed'})

        if picking.sale:
            picking.sale.state = 'manual'
