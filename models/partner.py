from openerp.osv import osv, fields


class ResPartner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
		'firstname': fields.char('Firstname'),
		'lastname': fields.char('Lastname'),
		'external_id': fields.integer('Magento ID', copy=False, select=True),
    }


    def get_or_create_customer(self, cr, uid, record, context=None):
	partner = self.search(cr, uid, [('external_id', '=', record['customer_id'])])
	if partner:
	    return self.browse(cr, uid, partner[0])

	else:
	    vals = {
		    'firstname': record['customer_firstname'],
		    'lastname': record['customer_lastname'],
		    'name': record['customer_firstname'] + ' ' + record['customer_lastname'],
		    'email': record['customer_email'],
		    'external_id': record['customer_id'],

	    }
	    partner = self.create(cr, uid, vals)

	    return self.browse(cr, uid, partner)


    def get_or_create_partner_address(self, cr, uid, address_data, \
		partner, context=None):

	if self.match_mage_address(cr, uid, partner, address_data):
	    return partner

	for address in partner.child_ids:
	    if self.match_mage_address(
		cr, uid, address, address_data
	    ):
	        break
	else:
	    address = self.create_mage_partner_address(
		cr, uid, address_data, partner, context
	    )

	return address


    def match_mage_address(self, cr, uid, address, address_data):
        # Check if the name matches
        if address.name != u' '.join(
            [address_data['firstname'], address_data['lastname']]
        ):
            return False

        address_data['street'] = address_data['street'].replace('\r', '\n')
        addr_lines = address_data['street'].split('\n')
	addr_line1 = addr_lines[0]

	if len(addr_lines) > 1:
	    addr_line2 = addr_lines[1]
	else:
	    addr_line2 = None

        if not all([
            (address.street or None) == addr_line1,
	    (address.street2 or None) == addr_line2,
            (address.zip or None) == address_data['postcode'],
            (address.city or None) == address_data['city'],
            (address.phone or None) == address_data['telephone'],
            (address.fax or None) == address_data['fax'],
            (address.country_id and address.country_id.code or None) ==
                address_data['country_id'],
            (address.state_id and address.state_id.name or None) ==
                address_data['region']
        ]):
            return False

        return True


    def create_mage_partner_address(self, cr, uid, address_data, partner, context=None):
        country_obj = self.pool.get('res.country')
        state_obj = self.pool.get('res.country.state')

        country = country_obj.search_using_magento_code(
            cr, uid, address_data['country_id'], context
        )
        if address_data['region']:
            state_id = state_obj.find_or_create_using_magento_region(
                cr, uid, country, address_data['region'], context
            ).id
        else:
            state_id = None


        address_data['street'] = address_data['street'].replace('\r', '\n')
        addr_lines = address_data['street'].split('\n')
        addr_line1 = addr_lines[0]

        if len(addr_lines) > 1:
            addr_line2 = addr_lines[1]
        else:
            addr_line2 = None

        address_id = self.create(cr, uid, {
            'name': u' '.join(
                [address_data['firstname'], address_data['lastname']]
            ),
            'street': addr_line1,
            'street2': addr_line2,
            'state_id': state_id,
            'country_id': country.id,
            'city': address_data['city'],
            'zip': address_data['postcode'],
            'phone': address_data['telephone'],
            'fax': address_data['fax'],
            'parent_id': partner.id,
        }, context=context)

        return self.browse(cr, uid, address_id, context=context)
