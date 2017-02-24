from openerp.osv import osv, fields
from openerp.tools.translate import _
CARRIER_MAP = {'ups': 'UPS', 'fedex': 'FedEx'}

class DeliveryCarrier(osv.osv):
    _inherit = 'delivery.carrier'
    _columns = {
	'display_in_ui': fields.boolean('Display in Searches'),
	'mage_code': fields.char('Magento ID', select=True, copy=False),
	'mage_carrier_code': fields.char('Magento Carrier Code'),
	'channel_name': fields.char('Channel Name'),
	'channel_color': fields.char('Channel Color'),
	'mage_carrier': fields.selection([('ups', 'UPS'),
					  ('usps', 'USPS'),
					  ('fedex', 'FedEx'),
					  ('dhl', 'DHL'),
	], 'Carrier', select=True),
    }

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False):
        """ Check presence of key 'consolidate_children' in context to include also the Consolidated Children
            of found accounts into the result of the search
        """

	args.append(('display_in_ui', '=', True))
        res = super(DeliveryCarrier, self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)
	return res


    def prepare_odoo_record_vals(self, cr, uid, job, record):
	mage = job.mage_instance

	if not mage.default_shipping_partner:
	    raise osv.except_osv(_('Config Error'), _('No Shipping Partner Defined!'))

	if not mage.shipping_product:
	    raise osv.except_osv(_('Config Error'), _('No Shipping Product Defined!'))

	method = record.get('method_title') or record.get('code')

	method = method.replace('UPS ', '')
	code_name = CARRIER_MAP.get(record.get('carrier_code')) or ''
	vals = {'mage_code': method,
		'display_in_ui': True,
		'name': ' '.join([code_name, method]) if record.get('carrier_code') else method,
		'mage_carrier_code': record.get('carrier_code'),
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
