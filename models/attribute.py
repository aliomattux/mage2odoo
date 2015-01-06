from openerp.osv import osv, fields
from pprint import pprint as pp
from lxml import etree
from openerp.tools.translate import _



class ProductAttributeSet(osv.osv):
    _name = 'product.attribute.set'
    _description = "Product Attribute Set"

    def _attribute_ids(self, cr, uid, ids, fieldname, arg, context=None):
	id = ids[0]
	query = "SELECT attribute.attribute_id\n" \
	"FROM product_attribute_group gr\n" \
	"JOIN product_attribute_set set ON (gr.set = set.id)\n" \
	"JOIN product_group_attribute_rel attribute ON (gr.id = attribute.group_id)\n" \
	"WHERE set.id = %s" % id
	cr.execute(query)
	results = cr.fetchall()
	print results
	return True

    _columns = {
	'external_id': fields.integer('External Id', select=True, copy=False),
	'name': fields.char('Name'),
	'groups': fields.one2many('product.attribute.group', 'set', 'Attribute Groups'),
	'attributes': fields.function(_attribute_ids, method=True, type="boolean", store=False, string="Attributes"),
    }


    def prepare_odoo_record_vals(self, cr, uid, job, record):
        return {
                'name': record['name'],
                'external_id': record['set_id'],
        }


class ProductAttributeGroup(osv.osv):
    _name = 'product.attribute.group'
    _description = "Product Attribute Group"
    _order = 'sort_order'
    _columns = {
	'external_id': fields.integer('External Id', select=True, copy=False),
	'name': fields.char('name'),
	'set': fields.many2one('product.attribute.set', 'Attribute Set'),
	'default': fields.integer('Default'),
	'sort_order': fields.integer('Sort Order'),
	'attributes': fields.many2many('product.attribute',
		'product_group_attribute_rel', 'group_id', 'attribute_id', 'Attributes'),
    }


    def prepare_odoo_record_vals(self, cr, uid, job, record):
	set_obj = self.pool.get('product.attribute.set')
        return {
                'default': record['default_id'],
                'set': set_obj.get_mage_record(cr, uid, record['attribute_set_id']),
                'sort_order': record['sort_order'],
                'external_id': record['attribute_group_id'],
                'name': record['attribute_group_name'],
        }


class ProductAttribute(osv.osv):
    _inherit = 'product.attribute'


    def _frontend_options(self):
        return {
                'select': 'many2one',
                'text': 'char',
                'date': 'date',
		'hidden': 'boolean',
		'datetime': 'datetime',
		'multiline': 'char',
                'boolean': 'boolean',
                'textarea': 'text',
		'image': 'binary',
                'multiselect': 'many2many',
                'price': 'float',
		'weight': 'float',
                'media_image': 'binary',
                'gallery': 'binary',
        }

    def _get_boolean(self, field):
        return True if field == '1' else False


    _columns = {
	'id': fields.integer('ID'),
	'apply_to': fields.selection([('all_types', 'All Product Types'),
				      ('select_types', 'Selected Product Types')
	],'Apply To'),
#	'apply_to_selections': fields.many2many('mage.product.type', 'mage_attribute_prod_type_rel', 
#		'attribute', 'type', 'Selections'),
	'external_id': fields.char('External Id', select=True, copy=False),
	'attribute_code': fields.char('Attribute Code', select=True),
	'default_value': fields.char('Default Value'),
	'ttype': fields.char('Odoo Model Field Type'),
        'frontend_input': fields.selection([
		('select', 'Dropdown'),
                ('text', 'Text Field'),
                ('date', 'date'),
                ('hidden', 'Hidden'),
                ('datetime', 'Date'),
                ('multiline', 'Multi Line'),
                ('boolean', 'Yes/No'),
                ('textarea', 'Text Area'),
                ('image', 'Image'),
                ('multiselect', 'Multiple Select'),
                ('price', 'Price'),
                ('weight', 'Weight'),
                ('media_image', 'Media Image'),
                ('gallery', 'Gallery')
	], 'Catalog Input Type'),
	'name': fields.char('Frontend Label'),
	'is_comparable': fields.boolean('Comparable on Front-end'),
	'is_configurable': fields.boolean('Use to Create Configurable Product'),
	'is_filterable': fields.selection([
					   ('0', 'No'),
					   ('1', 'Filterable (with results)'),
					   ('2', 'Filterable (no results)')
	], 'Use in Layered Navigation'),
	'scope': fields.selection([('0', 'Store View'),
				   ('1', 'Global'),
				   ('2', 'Website')
	], 'Scope', help="Declare attribute value saving scope"),
	'is_filterable_in_search': fields.boolean('Use In Search Results Layered Navigation',
		help="Can be used only with catalog input type Dropdown, Multiple Select and Price"),
	'is_html_allowed_on_front': fields.boolean('Allow HTML Tags on Frontend'),
	'is_required': fields.boolean('Values Required'),
	'is_searchable': fields.boolean('Use in Quick Search'),
	'is_unique': fields.boolean('Unique Value'),
	'is_used_for_price_rules': fields.boolean('is_used_for_price_rules'),
	'is_used_for_promo_rules': fields.boolean('Use for Promo Rules Conditions'),
	'is_user_defined': fields.boolean('User Attribute'),
	'is_visible': fields.boolean('System Hidden Attribute'),
	'is_visible_in_advanced_search': fields.boolean('Use in Advanced Search'),
	'is_visible_on_front': fields.boolean('Visible on Catalog Pages on Front-end'),
	'is_wysiwyg_enabled': fields.boolean('Enable WYSIWYG'),
	'note': fields.char('Note'),
	'position': fields.integer('Position'),
	'used_for_sort_by': fields.boolean('Used for Sorting in Product Listing'),
	'used_in_product_listing': fields.boolean('Used in Product Listing'),
    }

    def prepare_odoo_record_vals(self, cr, uid, job, record):
	dict = self._frontend_options()
        return {
                'is_visible': self._get_boolean(record['is_visible']),
                'ttype': dict[record['frontend_input']],
                'is_wysiwyg_enabled': self._get_boolean(record['is_wysiwyg_enabled']),
                'is_used_for_promo_rules': self._get_boolean(record['is_used_for_promo_rules']),
                'is_configurable': self._get_boolean(record['is_configurable']),
                'is_searchable': self._get_boolean(record['is_searchable']),
                'scope': record['is_global'],
                'is_visible_in_advanced_search': self._get_boolean(record['is_visible_in_advanced_search']),
                'is_user_defined': self._get_boolean(record['is_user_defined']),
                'default_value': record['default_value'],
                'frontend_input': record['frontend_input'],
                'name': record['frontend_label'],
                'is_filterable_in_search': self._get_boolean(record['is_filterable_in_search']),
                'is_required': self._get_boolean(record['is_required']),
                'is_filterable': record['is_filterable'],
                'used_in_product_listing': self._get_boolean(record['used_in_product_listing']),
                'is_used_for_price_rules': self._get_boolean(record['is_used_for_price_rules']),
                'position': record['position'],
                'attribute_code': record['attribute_code'],
                'is_unique': self._get_boolean(record['is_unique']),
                'external_id': record['attribute_id'],
                'is_comparable': self._get_boolean(record['is_comparable']),
        }


class ProductAttributeValue(osv.osv):
    _inherit = 'product.attribute.value'

    _columns = {
        'external_id': fields.char('External Id', select=True, help="The Option id from Magento"),
        'name': fields.char('Admin', translate=True, required=True),
        'attribute_code': fields.related('attribute_id', 'attribute_code',
                type="char", relation="product.attribute", store=True, string="Attribute Code"
        ),
    }

    def prepare_odoo_record_vals(self, cr, uid, job, record):
	attribute_obj = self.pool.get('product.attribute')

        return {
                'attribute_id': attribute_obj.get_mage_record(cr, uid, record['attribute_id']),
                'external_id': record['value'],
                'name': record['label'],
        }


    #Needed for temp hack
    def upsert_mage_record(self, cr, uid, vals):
        existing_sets = self.search(cr, uid, [('external_id', '=', vals['external_id'])])
        if not existing_sets:
                existing_sets = self.search(cr, uid, [('attribute_id', '=', vals['attribute_id']), ('name', '=', vals['name'])])

        if existing_sets:
            self.write(cr, uid, existing_sets[0], vals)
            return(False, existing_sets[0])
        else:
            self.create(cr, uid, vals)
            return True
