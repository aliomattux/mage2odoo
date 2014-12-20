from openerp.osv import osv, fields
from openerp.tools.translate import _

class DeliveryCarrier(osv.osv):
    _inherit = 'delivery.carrier'
    _columns = {
	'mage_code': fields.char('Magento ID', select=True, readonly=True),
	'mage_carrier': fields.selection([('ups', 'UPS'),
					  ('usps', 'USPS'),
					  ('fedex', 'FedEx'),
					  ('dhl', 'DHL'),
	], 'Carrier', select=True),
    }


    def prepare_odoo_record_vals(self, cr, uid, job, record):
	mage = job.mage_instance

	if not mage.default_shipping_partner:
	    raise osv.except_osv(_('Config Error'), _('No Shipping Partner Defined!'))

	if not mage.shipping_product:
	    raise osv.except_osv(_('Config Error'), _('No Shipping Product Defined!'))

	vals = {'mage_code': record['code'],
		'name': record['label'],
		'product_id': mage.shipping_product.id,
		'partner_id': mage.default_shipping_partner.id,

	}

	return vals


    #Override to use code field instead of internal id
    def get_mage_record(self, cr, uid, external_id):
        existing_ids = self.search(cr, uid, [('mage_code', '=', external_id)])
        if existing_ids:
            return existing_ids[0]

        return False


    def upsert_mage_record(self, cr, uid, vals, record_id=False):
        if record_id:
            self.write(cr, uid, record_id, vals)
            return record_id

        existing_id = self.get_mage_record(cr, uid, vals['mage_code'])

        if existing_id:
            self.write(cr, uid, existing_id, vals)
            return existing_id

        else:
            return self.create(cr, uid, vals)
