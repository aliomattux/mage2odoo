from openerp import SUPERUSER_ID, api
from openerp.osv import osv, fields


class StockMove(osv.osv):
    _inherit = 'stock.move'

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

        if moves[0].procurement_id.sale_line_id:
	    picking = moves[0].picking_id
	    vals = self.add_sale_vals(cr, uid, moves[0].procurement_id.sale_line_id.order_id)
            picking_obj.write(cr, uid, picking.id, vals)

        return res
