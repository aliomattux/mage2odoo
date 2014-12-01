from openerp.osv import osv, fields
from openerp.tools.translate import _
import cStringIO
import csv
import base64


class MageImportWizard(osv.osv_memory):
    _name = 'mage.import.wizard'
    _columns = {
        'file': fields.binary('Input File'),
        'file_name': fields.char('File Name', size=64),
    }

    def import_products(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context=context)
        file = wizard.file
        data = base64.decodestring(file)
        input = cStringIO.StringIO(data)
        reader = csv.DictReader(input, quotechar='"', delimiter=',')
        product_obj = self.pool.get('product.product')
        error_count = 0
        for row in reader:
	    print row

	return True


class MageExportWizard(osv.osv_memory):
    _name = 'mage.export.wizard'
