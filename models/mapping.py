from openerp.osv import osv, fields
from pprint import pprint as pp

class MageMapping(osv.osv):
    _name = 'mage.mapping'


    def _get_related_model_ids(self, cr, uid, ids, name, arg, context=None):
        "Used to retrieve model field one can map without ambiguity. Fields come from Inherited objects"
        res = {}
        for mapping in self.browse(cr, uid, ids, context): #FIXME: could be fully recursive instead of only 1 level
            main_model = mapping.model_id.model
            inherits_model = [x for x in self.pool.get(main_model)._inherits]
            model_ids = [mapping.model_id.id] + self.pool.get('ir.model').search(cr, uid, [['model','in', inherits_model]], context=context)
            res[mapping.id] = model_ids
        return res


    def _related_model_ids(self, cr, uid, model, context=None):
        inherits_model = [x for x in self.pool.get(model.model)._inherits]
        model_ids = [model.id] + self.pool.get('ir.model').search(cr, uid, [['model','in', inherits_model]], context=context)
        return model_ids


    _columns = {
        'name': fields.char('Name', required=True),
	'magento_id_fieldname': fields.char('Magento Id Fieldname'),
	'related_model_ids': fields.function(_get_related_model_ids, type="many2many", relation="ir.model", string='Related Inherited Models'),
        'model_id': fields.many2one('ir.model', 'Odoo Object', required=True, ondelete='cascade'),
        'model':fields.related('model_id', 'model', type='char', string='Object Name'),
        'mapping_lines': fields.one2many('mage.mapping.line',
                                        'mapping',
                                        'Mapping Lines'),
    }


class MageMappingLine(osv.osv):
    _name = 'mage.mapping.line'
    _rec_name = 'field'
    _columns = {
        'mapping': fields.many2one('mage.mapping', "Mapping", select=True),
	'field': fields.many2one('ir.model.fields', 'Odoo Field', ondelete='cascade'),
	'internal_type': fields.related('field','ttype', type="char", relation='ir.model.field', string='Internal Type'),
	'relation': fields.related('field', 'relation', type="char", string="Relation"),
	'type': fields.selection([('in_out', 'Magento <-> Odoo'), ('in', 'Magento -> Odoo'), ('out', 'Magento <- Odoo')], 'Type'),
	'internal_field': fields.related('field', 'name', type='char', relation='ir.model.field', string='Field name',readonly=True),
	'datetime_format': fields.char('Datetime Format', size=32),
        'child_mapping': fields.many2one('mage.mapping', 'Child Mapping'),
        'mage_fieldname': fields.char('External Field Name', size=128),
        'mapping_type': fields.selection([('sub-mapping','Sub Mapping Line'),
                			  ('direct', 'Direct Mapping'),
					  ('function', 'Function'),
	], 'Evalution Type', required=True),
	'function_name': fields.char('Function Name', help="Function must inherit class mage.integrator"),
        'external_type': fields.selection([('datetime', 'Datetime'), ('unicode', 'String'), ('bool', 'Boolean'), ('int', 'Integer'),
                ('float', 'Float'), ('list', 'List'), ('dict', 'Dictionary')], 'External Type', required=True)
    }


    _defaults = {
         'type' : lambda * a: 'in_out',
         'external_type': lambda *a: 'unicode',
         'mapping_type': lambda *a: 'direct',
    }


class IrModel(osv.osv):
    _inherit = 'ir.model'
    _columns = {
	'mage_info_method': fields.char('Magento Info Method'),
	'mage_create_mapping': fields.many2one('mage.mapping', 'Info Mapping'),

    }
