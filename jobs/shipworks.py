from openerp.osv import osv, fields
from pprint import pprint as pp
import pytz
from datetime import datetime, timedelta

class MageJob(osv.osv):
    _inherit = 'mage.job'


    def reset_shipworks_orders(self, cr, uid, job, context=None):
        now = datetime.utcnow()
        central = pytz.timezone('US/Central')
        utc = pytz.timezone('UTC')
        utc_now = utc.localize(now)
#       final_value = utc_now.astimezone(central) - timedelta(hour$
        final_value = utc_now.astimezone(central)
        stamp = final_value.strftime('%Y-%m-%d')
	query = "UPDATE stock_picking SET sw_exp = False, sw_pre_exp = False WHERE write_date > '%s' OR create_date > '%s'" % (stamp, stamp)
	cr.execute(query)
	return True
