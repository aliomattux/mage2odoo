from openerp.osv import osv, fields


class ProductCategory(osv.osv):
    _inherit = 'product.category'
    _columns = {
	'external_id': fields.integer('External Id', select=True),
	'position': fields.integer('Position'),
	'mage_active': fields.boolean('Mage Active'),
    }


    def get_or_create_odoo_record(self, cr, uid, job, external_id):
        category_id = self.get_mage_record(cr, uid, external_id)
        if not category_id:
            category_id = self.get_and_create_mage_record(cr, uid, job, 'catalog_category.info', external_id)

        return self.browse(cr, uid, category_id)


    def prepare_odoo_record_vals(self, cr, uid, job, record):
        return {
            'name': record['name'],
            'parent_id': self.get_mage_record(cr, uid, record['parent_id']),
            'external_id': record['category_id'],

        }
