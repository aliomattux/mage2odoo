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

    def _prepare_picking_assign_vals(self, cr, uid, move, context=None):
        vals = {
                'origin': move.origin,
                'company_id': move.company_id and move.company_id.id or False,
                'move_type': move.group_id and move.group_id.move_type or 'direct',
                'partner_id': move.partner_id.id or False,
                'picking_type_id': move.picking_type_id and move.picking_type_id.id or False,
        }


	if move.procurement_id.sale_line_id:
	    vals.update(self.add_sale_vals(cr, uid, move.procurement_id.sale_line_id.order_id))

        return vals

    #This method is overridden because there is no way I know of to add to the vals of a picking record when it is created
    #There are lots of reasons to add something to a stock.picking if it is created from a sales order > procurement
    #IMO a proper solution would be to put values = {} into a prepare vals method so a developer can call super
    #to add to the vals without having to override a core method
    @api.cr_uid_ids_context
    def _picking_assign(self, cr, uid, move_ids, procurement_group, location_from, location_to, context=None):
        """Assign a picking on the given move_ids, which is a list of move supposed to share the same procurement_group, location_from and location_to
        (and company). Those attributes are also given as parameters.
        """
        pick_obj = self.pool.get("stock.picking")
        picks = pick_obj.search(cr, uid, [
                ('group_id', '=', procurement_group),
                ('location_id', '=', location_from),
                ('location_dest_id', '=', location_to),
                ('state', 'in', ['draft', 'confirmed', 'waiting'])], context=context)

        if picks:
            pick = picks[0]
        else:
            move = self.browse(cr, uid, move_ids, context=context)[0]
	    vals = self._prepare_picking_assign_vals(cr, uid, move)
            pick = pick_obj.create(cr, uid, vals, context=context)
        return self.write(cr, uid, move_ids, {'picking_id': pick}, context=context)
