from openerp.osv import osv
from openerp.tools.translate import _
import unicodedata

#This file was based on the original external_referentials module. Some code such as extend decorator
#are copied from it, other code is inspired by design

#Decorator function to create global method (Extend the object service)
def extend(class_to_extend):
    """
    Decorator to use to extend a existing class with a new method
    Example :
    @extend(osv.osv)
    def new_method(self, *args, **kwargs):
        print 'I am in the new_method', self._name
        return True
    Will add the method new_method to the class osv.osv
    """
    def decorator(func):
        if hasattr(class_to_extend, func.func_name):
            raise osv.except_osv(_("Developer Error"),
                _("You can extend the class %s with the method %s.",
                "This method already exists. Use the decorator 'replace' instead"))
        setattr(class_to_extend, func.func_name, func)
        return class_to_extend
    return decorator


@extend(osv.osv)
def upsert_odoo_record(self, cr, uid, filters, vals):
    existing_record = self.search(cr, uid, filters)
    if len(existing_record) > 1:
	raise osv.except_osv(_('User Error'), _('More than one result found!'))
    if existing_record:
	self.write(cr, uid, existing_record[0], vals)
	return (False, existing_record[0])

    else:
	return (True, self.create(cr, uid, vals))


@extend(osv.osv)
def _get_mappinglines(self, cr, uid, mapping, context=None):
    """
        Return a list dictionary of mappinglines for iteration
        :param :mapping id of a parent object mapping. Sale, Fulfillment, etc
        :return List of dictionary mapping lines
    """
    mapping_line_obj = self.pool.get('mage.mapping.line')
    if type(mapping) == list:
        operator = 'in'
    else:
        operator = '='
    mapping_line_ids = mapping_line_obj.search(cr, uid, [('mapping', operator, mapping)])
    mappinglines = mapping_line_obj.read(cr, uid, mapping_line_ids, \
	fields=['field', 'internal_type', 'relation', 'internal_field', 'child_mapping', 'mage_fieldname', 'mapping_type', 'function_name', 'external_type']
    )

    return mappinglines



@extend(osv.osv)
def _transform_record(self, cr, uid, job, record, conversion_type, mappinglines=False, context=None):
    """
        Convert External row of data into odoo data
        :param :conn Connection object to 
        :param :record Row of data from 
        :param :mapping Parent Mapping of a data type. Product, Sale, etc
        :param :conversion_type Import or Export
        :return :Dictionary of Converted data in odoo format

    """
    #Initialize the return
    vals = {}

    #Get the dictionary of mapping lines
    if not mappinglines:
        mappinglines = self._get_mappinglines(cr, uid, job.mapping.id)

    for line in mappinglines:
        #Import from Magento
        if conversion_type == 'from_mage_to_odoo':
            from_field = line['mage_fieldname']
            to_field = line['internal_field']
	#Export to Magento
	else:
            from_field = line['internal_field']
            to_field = line['mage_fieldname']

        if from_field in record.keys():

            #Get the field value from the response
            field_value = record.get(from_field)

            #Could be a straight map or a many2one
            if line['mapping_type'] == 'direct':
		if line['internal_type'] in ['many2many', 'one2many']:
		    result_list = []
		    rel_obj = self.pool.get(line['relation'])
		    if field_value:
			if type(field_value) == str:
			    field_value = field_value.split(',')
		        found_ids = rel_obj.search(cr, uid, [('external_id', 'in', field_value)])
		    else:
			found_ids = []
	#	    for x in field_value:
	#		res = self._transform_field(cr, uid, job, x, line, conversion_type)
	#		if not res:
	#		    continue
	#		result_list.append(res)
		    vals[to_field] = [(6, 0, found_ids)]

		else:
                    #Transform a specific field
                    vals[to_field] = self._transform_field(cr, uid, job, field_value, line, conversion_type)


            elif line['mapping_type'] == 'sub-mapping' and line['internal_type'] == 'many2one':
		#Determine the usage for this block
		raise
                field = line['field'][0]
                related_obj_name = self.pool.get('ir.model.fields').browse(cr, uid, int(field)).relation
                related_obj = self.pool.get(related_obj_name)
                resp = related_obj._transform_record_into_many2one(cr, uid, job, record, line, conversion_type)
                if resp:
                    vals[to_field] = resp

	    #Custom Function
	    else:
		#TODO: Fixme
	        vals.update(getattr(self, line['function_name'])(cr, uid, job, conversion_type, line, record))

    return vals


def _transform_record_into_many2one(self, cr, uid, job, record, line, conversion_type):
    try:
        vals = self._transform_record(cr, uid, job, record, \
            [line['child_mapping'][0]], conversion_type)

        search_filters = self.get_key_search_filters(cr, uid, line['child_mapping'][0], vals)
        existing_ids = self.search(cr, uid, search_filters)
        if existing_ids:
            self.write(cr, uid, existing_ids[0], vals)
            return existing_ids[0]

        else:
            return self.create(cr, uid, vals)

    except Exception, e:
        raise

@extend(osv.osv)
def _transform_field(self, cr, uid, job, field_value, line, conversion_type, context=None):
    """
	Type transformation of a field. Depending on the mappingline type, return a direct field mapping
	or a foreign key from  data
	:param :field_value  Field value
	:param :line odoo mapping line
	:return odoo compatible field value
    """
    #Return Field initialized
    field = False
    #External type is python data type, str, unicode, float, int, etc
    external_type = line['external_type']
    #Internal type can include many2one, one2many, etc
    internal_type = line['internal_type']
    #Field that gets updated
    internal_field = line['internal_field']

    #FIXME: Implement datetime and functional fields
    #Ensure the field passed is not null
    if not (field_value is False or field_value is None or not field_value):

	#If it is some kind of relational field
	if internal_type in ['many2one', 'many2many', 'one2many'] \
		and line['mapping_type'] == 'direct':
	    related_obj = self.pool.get(line['relation'])
	    if conversion_type == 'from_mage_to_odoo':
	        return related_obj.get_or_create_odoo_record(cr, uid, job, line, field_value)

	    #Export Functionality
	    else:
	        return related_obj.get_or_create_external_record(cr, uid, line, field_value)

	    #String, Integer, Float

	#Support for special types
        elif external_type == 'dict' and internal_type == 'integer':
	    if type(field_value) != dict:
		raise osv.except_osv(_('Error!'),_("External Field is of type %s But type specified is %s for Field %s"%(type(field_value), external_type, line['mage_fieldname'])))

	    if field_value['internalid']:
                field = eval('int')(field_value['internalid'])
	    else:
		field = False

        elif external_type == 'dict' and internal_type in ['char', 'selection']:
            if type(field_value) != dict:
                raise osv.except_osv(_('Error!'),_("External Field is of type %s But type specified is %s for Field %s"%(type(field_value), external_type, line['mage_fieldname'])))

	    if type(field_value['name']) == unicode:
		field_value['name'] = unicodedata.normalize('NFKD', field_value['name']).encode('ascii','ignore')
            field = eval('str')(field_value['name'])

	else:
	    if external_type == 'bool':
		if field_value in ['1', True]:
		    return True
		else:
		    return False


            elif external_type == "datetime":
                if not field_value:
                    field_value = False
                else:
                    datetime_format = line['datetime_format']
		    if not datetime_format:
			raise osv.except_osv(_('Error!'),_("Date field passed but no format specified!"))
                    if conversion_type == 'from_mage_to_odoo':
                        datetime_value = datetime.strptime(field_value, datetime_format)
                        if internal_type == 'date':
                            return datetime_value.strftime(DEFAULT_SERVER_DATE_FORMAT)
                        elif internal_type == 'datetime':
			    local_timestamp = local_timezone.localize(datetime_value)
			    return local_timestamp.astimezone(utc).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                         #   return datetime_value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    else:
                        if internal_type == 'date':
                            datetime_value = datetime.strptime(field_value, DEFAULT_SERVER_DATE_FORMAT)
                        elif internal_type == 'datetime':
                            datetime_value = datetime.strptime(field_value, DEFAULT_SERVER_DATETIME_FORMAT)

                        return datetime_value.strftime(datetime_format)

	    if external_type == 'float':
		if not field_value:
		    field_value = 0
		if field_value and line['reverse_float']:
		    return ff(eval(external_type)(field_value))

	    if type(field_value) not in [str, float, int, unicode]:
		raise osv.except_osv(_('User Config Error!'),_("External Type is %s  for field %s which is not compatible with Character or Number based Fields!") % (type(field_value), line['mage_fieldname']))
	    if type(field_value) == unicode:
		field_value == unicodedata.normalize('NFKD', field_value).encode('ascii','ignore')

	    field = eval(external_type)(field_value)

    #Return formatted field
    return field



@extend(osv.osv)
def get_or_create_odoo_record_deprecated(self, cr, uid, job, line, field_value, model=False, context=None):
    """
	Try to locate an existing external record. Return it.
	If no record can be found, call the external system and create it on the fly

    """

    #Find an external record
    #TODO: This could be big issue here...
    existing_id = self.search(cr, uid, [('external_id', '=', field_value)])
    if existing_id:
	return existing_id[0]
    #No existing external id was found. Next we determine if this object has a mapping
    #If there is a mapping, we will call the external system and import the reference
    #If there is no mapping, we will create the reference with only internalid and name
    else:

	if model:
            query = "SELECT model.mage_create_mapping, model.mage_info_method" + \
            "\nFROM ir_model model" + \
            "\nWHERE model.model = '%s'"% model + \
            "\nAND model.mage_create_mapping IS NOT NULL"

	else:
	    query = "SELECT model.mage_create_mapping, model.mage_info_method" + \
	    "\nFROM ir_model_fields fields" + \
	    "\nJOIN ir_model model ON (fields.relation = model.name)" + \
	    "\nWHERE fields.id = %s"% line['field'][0] + \
	    "\nAND model.mage_create_mapping IS NOT NULL"

	cr.execute(query)
	results = cr.dictfetchone()
	if results:
	    vals = self.load_and_transform_external_record(cr, uid, job, results, field_value)
	    if not vals:
		return None

            return self.create(cr, uid, vals)

	else:
	    return None


@extend(osv.osv)
def get_or_create_external_record(self, cr, uid, line, field_value, context=None):
    """
        Try to locate an existing external record. Return it.
        If no record can be found, call the external system and create it on the fly
        :param :mline Mapping line in odoo
        :param :field_value The field data returned by 

    """
    #FIXME: Understand the total effect of this design.

    mapping_obj = self.pool.get('mage.mapping')
    existing_record = self.browse(cr, uid, field_value[0])
    internalid = existing_record.internalid
    #Found a match so return it
    if internalid and internalid > 0:
        return internalid

    #We could not find any existing record
    else:
        #Find a mapping id to export the record. If none can be found, try to create the record with id and name only
        mapping = mapping_obj.search(cr, uid, [('integration_id', '=', integration.id), \
                ('external_model', '=', line['recordtype'])])

        if not mapping:
	    print 'Your Screwed'
	    raise

	#FIXME: Is this the best way to do this?
	record = self.read(cr, uid, field_value[0])
	conversion_type = 'from_mage_to_odoo'
	job = False
	#FIXME: Understand the effect of this considering this method is already called, and could potentially recurse many times
        vals = self._transform_record(cr, uid, job, record, mapping, conversion_type)
	#Create and return the external record id
	return self._upsert_external_record(cr, uid, vals, field_value[0], line['recordtype'])




###This method to be deprecated in place of hybrid mapping system
@extend(osv.osv)
def load_and_transform_external_record(self, cr, uid, job, call_dict, external_id, context=None):
    """
    """
    mappinglines = self._get_mappinglines(cr, uid, call_dict['mage_create_mapping'])
    mage_obj = self.pool.get('mage.integrator')
    credentials = mage_obj._get_credentials(job)
    response = mage_obj._mage_call(credentials, call_dict['mage_info_method'], [external_id])
    if not response:
	return {}

    vals = self._transform_record(cr, uid, job, response, 'from_mage_to_odoo', mappinglines)
    #FIXME: Fix these hardcoded values
    return vals



@extend(osv.osv)
def get_and_create_mage_record(self, cr, uid, job, method, external_id):
    mage_obj = self.pool.get('mage.integrator')
    credentials = mage_obj._get_credentials(job)
    record = mage_obj._mage_call(credentials, method, [external_id])
    if not record:
	raise osv.except_osv(_('Data Error'), _('Call was successful but no data returned for reference: %s')%external_id)	
    return self.create_mage_record(cr, uid, job, record)


@extend(osv.osv)
def create_mage_record(self, cr, uid, job, record, context=None):
    vals = self.prepare_odoo_record_vals(cr, uid, job, record)
    return self.create(cr, uid, vals)


@extend(osv.osv)
def get_mage_record(self, cr, uid, external_id):
    existing_ids = self.search(cr, uid, [('external_id', '=', external_id)])
    if existing_ids:
	return existing_ids[0]

    return False


@extend(osv.osv)
def upsert_mage_record(self, cr, uid, vals, record_id=False):
    if record_id:
	self.write(cr, uid, record_id, vals)
        return record_id

    existing_id = self.get_mage_record(cr, uid, vals['external_id'])

    if existing_id:
	self.write(cr, uid, existing_id, vals)
	return existing_id

    else:
	return self.create(cr, uid, vals)
