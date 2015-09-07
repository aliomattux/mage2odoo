from openerp.osv import osv, fields
from pprint import pprint as pp

class ResPartner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
		'firstname': fields.char('Firstname'),
		'company': fields.char('Company'),
		'is_default_billing': fields.boolean('Is Default Billing'),
		'is_default_shipping': fields.boolean('Is Default Shipping'),
		'lastname': fields.char('Lastname'),
		'external_address_id': fields.integer('Magento Address Id', readonly=True),
		#'address_type': fields.selection([('billing', 'Billing'), ('shipping', 'Shipping')], 'Magento Address Type'),
		'external_id': fields.integer('Magento ID', copy=False, select=True, readonly=True),
    }


    def get_sale_address(self, cr, uid, partner_id, type, context=None):
	base_search = ('parent_id', '=', partner_id)
	if type == 'invoice':
	    preferred = 'is_default_billing'
	elif type == 'delivery':
	    preferred = 'is_default_shipping'
	else:
	    preferred = False

	if preferred:
	    preferred_ids = self.search(cr, uid, [(preferred, '=', True), ('type', '=', type), base_search])
	    if preferred_ids:
		return preferred_ids[0]

        address_ids = self.search(cr, uid, [('type', '=', type), base_search])
	if address_ids:
	    return address_ids[0]

	contact_ids = self.search(cr, uid, [('type', '=', 'contact'), base_search])
	if not contact_ids:
	    return partner_id

	return contact_ids[0]


    def sync_one_mage_customer(self, cr, uid, ids, context=None):
	integrator_obj = self.pool.get('mage.integrator')
	job_obj = self.pool.get('mage.job')
	job_ids = job_obj.search(cr, uid, [('python_function_name', '=', 'import_all_partners')])
	job = job_obj.browse(cr, uid, job_ids[0])

	partner = self.browse(cr, uid, ids[0])
	if not partner.external_id:
	    return True

	integrator_obj.import_partners(cr, uid, job, [partner.external_id])
	return True


    def get_or_create_customer(self, cr, uid, record, context=None):

        partner_ids = self.search(cr, uid, [('external_id', '=', \
            record['entity_id'])], limit=1)

	if partner_ids:
	    return self.browse(cr, uid, partner_ids[0])

	else:
	    firstname = record['firstname']
	    lastname = record['lastname'] or 'no lastname'
	    vals = {
		    'firstname': firstname,
		    'lastname': lastname,
		    'is_company': False,
		    'name': firstname + ' ' + lastname,
		    'email': record['email'],
		    'external_id': record['entity_id'],

	    }

	    #If there is a company in the parent record use that instead as this is a company
	    if record.get('addresses') and record['addresses'][0].get('company'):
		vals['is_company'] = True
		vals['name'] = record['addresses'][0]['company']

	    partner = self.create(cr, uid, vals)

	    return self.browse(cr, uid, partner)


    def get_or_create_order_customer(self, cr, uid, record, context=None):

	if record['customer_id'] == '0' or record.get('customer_is_guest') \
		and record.get('customer_is_guest') == '1':
	    partner_ids = []

	else:
	    partner_ids = self.search(cr, uid, [('external_id', '=', \
		record['customer_id'])], limit=1)

	if partner_ids:
	    return self.browse(cr, uid, partner_ids[0])

	else:
	    firstname = record['customer_firstname']
	    lastname = record['customer_lastname'] or 'no lastname'
	    vals = {
		    'firstname': firstname,
		    'lastname': lastname,
		    'is_company': False,
		    'name': firstname + ' ' + lastname,
		    'email': record['customer_email'],
		    'external_id': record['customer_id'],

	    }

	    #If there is a company in the parent record use that instead as this is a company
	    if record.get('billing_address') and record['billing_address'].get('company'):
		vals['is_company'] = True
		vals['name'] = record['billing_address']['company']

	    partner = self.create(cr, uid, vals)

	    return self.browse(cr, uid, partner)


    def get_or_create_partner_address(self, cr, uid, address_data, \
		partner, address_type, context=None):

	if not partner.child_ids:
	    return self.create_mage_partner_address(cr, uid, address_data, partner, context)
	
	for address in partner.child_ids:
	    if self.match_mage_address(
		cr, uid, address, address_data
	    ):
		address.company = address_data.get('company')
		if address_type:
		    address.type = address_type
		address.external_address_id = address_data.get('entity_id')
	        return address

        else:
            return self.create_mage_partner_address(
                cr, uid, address_data, partner, address_type, context
            )


    def parse_customer_address(self, cr, uid, address_data):
	#Build a dictionary of prepared address values
	#Also include an address object with no spaces for matching
	#an existing record
	vals = {}
        if address_data.get('street'):
            address_data['street'] = address_data['street'].replace('\r', '\n')
            addr_lines = address_data['street'].split('\n')
            addr_line1 = addr_lines[0]
            if len(addr_lines) > 1:
                addr_line2 = addr_lines[1].replace(' ', '') if addr_lines[1] else None
            else:
                addr_line2 = None
        else:
            addr_line1 = None
            addr_line2 = None

	vals = {
		'addr_1': addr_line1,
		'addr_1_match':addr_line1.replace(' ', '').lower() if addr_line1 else addr_line1,
                'addr_2': addr_line2,
                'addr_2_match': addr_line2.replace(' ', '').lower() if addr_line2 else addr_line2,
		'zip': address_data['postcode'],
		'zip_match': address_data['postcode'].replace(' ', '').lower() if address_data['postcode'] else address_data['postcode'],
		'city': address_data['city'],
		'city_match': address_data['city'].replace(' ', '').lower() if address_data['city'] else address_data['city'],
	}

	return vals


    def parse_odoo_address(self, cr, uid, address):
	street = address.street or None
	street2 = address.street2 or None
	zip = address.zip or None
	city = address.city or None

	vals = {
		'address': street.replace(' ', '').lower() if street else street,
		'address2': street2.replace(' ', '').lower() if street2 else street2,
		'zip': zip.replace(' ', '').lower() if zip else zip,
		'city': city.replace(' ', '').lower() if city else city,
	}

	return vals


    def match_mage_address(self, cr, uid, address, address_data):
        # Check if the name matches
	firstname = address_data['firstname']
	lastname = address_data['lastname'] or ''
	data_name = firstname + lastname
	final_data_name = data_name.replace(' ', '').lower()

	addr_name = address.name
	match_name = addr_name.replace(' ', '').lower()

	if match_name != final_data_name:
	    return False

	vals = self.parse_customer_address(cr, uid, address_data)
	match = self.parse_odoo_address(cr, uid, address)

        if not all([
            (match['address'] or None) == (vals['addr_1_match'] or None),
	    (match['address2'] or None) == (vals['addr_2_match'] or None),
            (match['zip'] or None) == (vals['zip_match'] or None),
            (match['city'] or None) == (vals['city_match'] or None),
        ]):

            return False

        return True


    def create_mage_partner_address(self, cr, uid, address_data, partner, address_type, context=None):
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

	vals = self.parse_customer_address(cr, uid, address_data)

	firstname = address_data['firstname']
	lastname = address_data['lastname'] or 'no lastname'
        address_id = self.create(cr, uid, {
            'name': u' '.join(
                [firstname, lastname]
            ),
	    'firstname': firstname,
	    'lastname': lastname,
	    'type': address_type,
	    'company': address_data.get('company'),
	    'external_address_id': address_data.get('entity_id'),
            'street': vals['addr_1'],
            'street2': vals['addr_2'],
            'state_id': state_id,
            'country_id': country.id,
            'city': vals['city'],
            'zip': vals['zip'],
            'phone': address_data['telephone'],
            'fax': address_data['fax'],
            'parent_id': partner.id,
        }, context=context)

        return self.browse(cr, uid, address_id, context=context)
