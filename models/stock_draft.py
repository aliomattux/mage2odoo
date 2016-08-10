from openerp import models, api, exceptions, _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.one
    def reset_picking_draft(picking):
        # go from canceled state to draft state
        if picking.state != 'cancel':
	    return True
        picking.move_lines.write({'state': 'draft'})
        picking.write({'state': 'draft'})
        picking.delete_workflow()
        picking.create_workflow()

        return True
