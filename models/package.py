from openerp.osv import osv, fields


class StockOutPackage(osv.osv):
    _inherit = 'stock.out.package'
    _columns = {
	'sale': fields.many2one('sale.order', select=True),
	'mage_package_state': fields.selection([('pending', 'Pending'),
						('exception', 'Exception'),
						('done', 'Dome')
	], 'Mage Package State', select=True),
    }

    _defaults = {
	'mage_package_state': 'pending',
    }


    def create(self, cr, uid, data, context=None):
	if data.get('picking'):
	    picking = self.pool.get('stock.picking').browse(cr, uid, data['picking'])
	    if picking.sale:
		data['sale'] = picking.sale.id

        return super(StockOutPackage, self).create(cr, uid, data, context=context)
