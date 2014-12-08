from openerp.osv import osv, fields


class StockOutPackage(osv.osv):
    _inherit = 'stock.out.package'
    _columns = {
	'mage_package_state': fields.selection([('pending', 'Pending'),
						('exception', 'Exception'),
						('done', 'Dome')
	], 'Mage Package State'),
    }

    _defaults = {
	'mage_package_state': 'pending',
    }
