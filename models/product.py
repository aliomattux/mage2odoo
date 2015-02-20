from openerp.osv import osv, fields
from magento import Product
from pprint import pprint as pp
from openerp.tools.translate import _

PRODUCT_TYPES = {
                'simple': 'product',
                'configurable': 'service',
                'bundle': 'service',
                'group': 'service',
                'virtual': 'service',
}


class ProductTemplate(osv.osv):
    _inherit = 'product.template'

    _columns = {
	'set': fields.many2one('product.attribute.set', 'Attribute Set'),
	'upc': fields.char('UPC', select=True),
	'short_description': fields.text('Short Descripton'),
	'categories': fields.many2many('product.category', 'mage_product_categories_rel', \
		'product_id', 'category_id', 'Categories'
	),
	'websites': fields.many2many('mage.website', 'mage_product_website_rel', 'product_tmpl_id', \
		'website_id', 'Websites'
	),
	'associated_products': fields.many2many('product.template', 'associated_products_rel', \
		'parent_id', 'product_tmpl_id', 'Associated Products', domain="[('mage_type', '!=', 'configurable')]"
	),
        'mage_tax_class': fields.many2one('product.attribute.value', 'Mage Tax Class',
                domain="[('attribute_code', '=', 'tax_class_id')]"),
	'visibility': fields.selection([
					('1', 'Not Visible Individually'),
					('2', 'Catalog'),
					('3', 'Search'),
					('4', 'Catalog, Search'),
	], 'Visibility'),
        'mage_status': fields.selection([
                                       ('1', 'Enabled'),
                                       ('2', 'Disabled'),
        ], 'Magento Status'),
        'mage_type': fields.selection([
                                       ('simple', 'Simple Product'),
                                       ('grouped', 'Grouped Product'),
                                       ('configurable', 'Configurable Product'),
                                       ('bundle', 'Bundle Product'),
				       ('ugiftcert', 'Gift Certificate'),
				       ('virtual', 'Virtual'),
        ], 'Mage Product Type'),
	'url_key': fields.char('URL Key'),
	'mage_manage_stock': fields.boolean('Manage Stock'),
	'external_id': fields.integer('External Id', select=True, copy=False),
	'sync_to_mage': fields.boolean('Magento Sync', copy=False),
        'super_attributes': fields.many2many('product.attribute',
                'product_super_attribute_rel', 'product_tmpl_id', 'attribute_id', 'Super Attributes',
		domain="[('scope', '=', '1'), ('is_configurable', '=', True), ('is_user_defined', '=', True), ('frontend_input', '=', 'select')]"),
    }

    def get_or_create_odoo_record(self, cr, uid, job, external_id):
	#This is not allowed
	raise


class ProductProduct(osv.osv):
    _inherit = 'product.product'


    _sql_constraints = [('default_code_uniq', 'unique (default_code)', 'The SKU must be unique!')]


    def get_or_create_odoo_record(self, cr, uid, job, external_id):
        product_id = self.get_mage_record(cr, uid, external_id)
	if not product_id:
	    product_id = self.get_and_create_mage_record(cr, uid, job, 'oo_catalog_product.info', external_id)

	return self.browse(cr, uid, product_id)


    def prepare_odoo_record_vals(self, cr, uid, job, record, context=None):
	set_obj = self.pool.get('product.attribute.set')
        vals = {
                'description': record.get('description', ' '),
                'mage_status': record['status'],
                'name': record['name'],
                'default_code': record['sku'],
                'mage_type': record['type_id'],
                'set': set_obj.get_mage_record(cr, uid, record['attribute_set_id']),
                'super_attributes': [(5)],
                'websites': [(5)],
                'external_id': record['entity_id'],
                'url_key': record.get('url_key', ''),
                'short_description': record.get('short_description', ''),
                'categories': [(5)],
                'type': PRODUCT_TYPES.get(record['type_id']) or 'product',
                'sync_to_mage': True,
        }

        if record.get('categories'):
            vals['categories'] = self._find_categories(cr, uid, record['categories']),

        if record.get('websites'):
            vals['websites'] = self._find_websites(cr, uid, record['websites'])

        if record.get('super_attributes'):
            vals['super_attributes'] = self._find_super_attributes(cr, uid, record['super_attributes'])

        return vals


    def _find_categories(self, cr, uid, categories):
        cat_obj = self.pool.get('product.category')
        category_ids = cat_obj.search(cr, uid, [('external_id', 'in', categories)])
        return [(6, 0, category_ids)]


    def _find_super_attributes(self, cr, uid, super_attributes):
        attribute_obj = self.pool.get('product.attribute')
        attribute_ids = attribute_obj.search(cr, uid, [('external_id', 'in', super_attributes)])
        return [(6, 0, attribute_ids)]


    def _find_websites(self, cr, uid, websites):
        website_obj = self.pool.get('mage.website')
        website_ids = website_obj.search(cr, uid, [('external_id', 'in', websites)])
        return [(6, 0, website_ids)]


    def _find_attribute_values(self, cr, uid, external_attribute_ids):
        attribute_obj = self.pool.get('product.attribute.value')
	external_ids = external_attribute_ids.split(',')
        attribute_ids = attribute_obj.search(cr, uid, [
                ('external_id', 'in', external_ids)
        ])

        return [(6, 0, attribute_ids)]


    def _find_attribute_value(self, cr, uid, external_attribute_id):
        attribute_obj = self.pool.get('product.attribute.value')

        attribute_ids = attribute_obj.search(cr, uid, [
                ('external_id', '=', external_attribute_id)
        ])

        if attribute_ids:
            return attribute_ids[0]

        return False


    def upsert_mage_record(self, cr, uid, vals, record_id=False):
        if record_id:
            self.write(cr, uid, record_id, vals)
            return record_id

        existing_id = self.get_mage_record(cr, uid, vals['external_id'])
        if not existing_id and vals.get('default_code'):
	    existing_id = self.search(cr, uid, [('default_code', '=', vals['default_code'])])

        if existing_id:
            self.write(cr, uid, existing_id, vals)
            return existing_id

        else:
            return self.create(cr, uid, vals)
