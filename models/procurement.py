from openerp import SUPERUSER_ID, api
from openerp.osv import osv, fields


class StockMove(osv.osv):
    _inherit = 'stock.move'
    _columns = {
	'sale_price': fields.float('Original Sale Price'),
	'sale_line_id': fields.many2one('sale.order.line', 'Sale Line ID'),
    }

    def add_sale_vals(self, cr, uid, sale, context=None):
	vals = {
	    'sale': sale.id,
	    'mage_store': sale.mage_store.id,
	}

	if sale.carrier_id:
	    vals['carrier_id'] = sale.carrier_id.id

	return vals


    @api.cr_uid_ids_context
    def _picking_assign(self, cr, uid, move_ids, procurement_group, \
                location_from, location_to, context=None):

        picking_obj = self.pool.get('stock.picking')

        res = super(StockMove, self)._picking_assign(cr, uid, move_ids, procurement_group, \
                location_from, location_to, context=context)

        moves = self.browse(cr, uid, move_ids)
	for move in moves:
            sale_line_id, price = self.find_sale_line_reference(cr, uid, move.product_id.id, move.procurement_id.sale_line_id.order_id.id)
	    if not sale_line_id:
		print 'NO SALE LINE ID'
		continue
	    move.sale_line_id = sale_line_id
	    move.sale_price = price
	    
        if moves[0].procurement_id.sale_line_id:
	    picking = moves[0].picking_id
	    vals = self.add_sale_vals(cr, uid, moves[0].procurement_id.sale_line_id.order_id)
            picking_obj.write(cr, uid, picking.id, vals)

        return res


    def find_sale_line_reference(self, cr, uid, product_id, order_id):
	sale_line_obj = self.pool.get('sale.order.line')
	sale_line_ids = sale_line_obj.search(cr, uid, [('product_id', '=', product_id), ('order_id', '=', order_id)])
	if not sale_line_ids:
	    return (False, False)
	sale_line = sale_line_obj.browse(cr, uid, sale_line_ids[0])
	return (sale_line.id, sale_line.price_unit)
