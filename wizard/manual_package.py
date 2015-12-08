from osv import osv, fields
from datetime import datetime

class ManualPackage(osv.osv_memory):
    _name = 'manual.package'
    _columns = {
        'fulfillment': fields.many2one('stock.transaction', 'Fulfillment Number'),
        'shipper': fields.char('Shipper'),
        'tracking_number': fields.char('Tracking Number'),
    }


    def button_create_package(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0])
        tran_obj = self.pool.get('stock.transaction')
        fulfillment = wizard.fulfillment
        package_obj = self.pool.get('stock.package')
        pack_number = len(fulfillment.packages) + 1
        vals = {
                'transaction': fulfillment.id,
                'tracking_number': wizard.tracking_number,
                'package_weight': 1,
                'package_number': pack_number,
                'workstation': 'Manual',
                'shipper': wizard.shipper,
        }

        package = package_obj.create(cr, uid, vals)
        tran_obj.write(cr, uid, fulfillment.id, {'state': 'shipped', 'date_done': datetime.utcnow()})

        return {'type': 'ir.actions.act_window_close'}
