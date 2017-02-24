from openerp.osv import osv, fields
from pprint import pprint as pp
from openerp.tools.translate import _
from datetime import datetime, timedelta

HOLDED_STATUSES = ['new', 'pending', 'holded']
CANCELED_STATUSES = ['canceled', 'closed']

class SaleOrder(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'mage_shipment_code': fields.char('Magento Shipping Code'),
        'mage_custom_status': fields.char('Magento Custom Status'),
    }


class MageIntegrator(osv.osv_memory):

    _inherit = 'mage.integrator'

    def wrapper_update_odoo_orders(self, cr, uid, job, context=None):
	try:
	    self.update_odoo_orders(cr, uid, job, context=context)
	except Exception, e:
	    print e
	    html = 'Alert! The Magento to Odoo Update job has failed.'
            recipients_data = [
                {'name': 'Email', 'email': 'email@email.com'},
            ]

            sender = 'alerts@odoo.odoo.com'
            subject = 'Update Script Alert'
            from_mail = "Alerts <alerts@odoo.odoo.com>"
	    self.send_error_notification(html, recipients_data, sender, subject, from_mail)

	return True


    def update_odoo_orders(self, cr, uid, job, context=None):
        """ See if order status is changed in Magento. If so then update it in Odoo
        """
        storeview_obj = self.pool.get('mage.store.view')
        sale_obj = self.pool.get('sale.order')
        picking_obj = self.pool.get('stock.picking')
        procurement_obj = self.pool.get('procurement.order')

        store_ids = storeview_obj.search(cr, uid, [('do_not_import', '=', False)])
        mappinglines = self._get_mappinglines(cr, uid, job.mapping.id)
        instance = job.mage_instance
        #Get a list of all orders updated in the last 24 hours
        from_date = (datetime.utcnow() - timedelta(days=2)).strftime('%Y-%m-%d')

        for storeview in storeview_obj.browse(cr, uid, store_ids):
            filters = {
                'store_id': {'=': storeview.external_id},
                'updated_at': {'gteq': {'from':from_date}},
                'created_at': {'gteq': {'from': '2016-03-01'}}
            }

            #Get list of IDS
            order_data = self._get_job_data(cr, uid, job, 'sales_order.search', [filters])
            if not order_data:
                continue

            #For each order in the response of orders updated
            for order in order_data:
                increment_id = order['increment_id']

                #Check Magento Status
                mage_status = order.get('status')
                if not mage_status:
                    continue

                #Find sales in Odoo that match the given id
                #an improvement would be to search with also mage_status to reduce loading records
                sale_ids = sale_obj.search(cr, uid, [('mage_order_number', '=', increment_id)])
                if not sale_ids:
                    continue

                sale = sale_obj.browse(cr, uid, sale_ids[0])

                #if the mage_status in Odoo matches the mage_status in Magento, then no action is needed
                if sale.mage_custom_status == mage_status:
                    continue

                #if the order is held in Odoo but has been released in Magento and not canceled
                if sale.mage_custom_status in HOLDED_STATUSES and mage_status not in HOLDED_STATUSES and mage_status != 'canceled':
                    self.mage_unhold_order(cr, uid, sale, mage_status)

                #No matter what happens to the order, if the status has changed ensure it updates in shipworks
                self.mage_status_changed(cr, uid, sale, mage_status)

                #RULE 2 - If the order is pending then unreserve any reserved inventory
                if mage_status in HOLDED_STATUSES:
                    self.mage_status_pending(cr, uid, sale)


                elif mage_status in CANCELED_STATUSES and sale.state != 'cancel':
                    self.mage_status_canceled(cr, uid, job, sale)


                #RULE 4 - If the order is complete in Magento but is not detected as shipped in Odoo
                elif mage_status == 'complete' and not sale.shipped:
                    self.mage_status_complete(cr, uid, sale)

        return True


    def mage_status_canceled(self, cr, uid, job, sale, context=None):
	print 'Cancelling Order', sale.name
        return self.cancel_one_order(cr, uid, job, sale, False)


    def mage_status_complete(self, cr, uid, sale, context=None):
	sale_obj = self.pool.get('sale.order')
	picking_obj = self.pool.get('stock.picking')

        if sale.state == 'draft':
            self.confirm_one_order(cr, uid, sale)

        if sale.state == 'cancel':
            sale.state = 'draft'
            self.confirm_one_order(cr, uid, sale)

        for picking in sale.picking_ids:
	    if picking.state != 'done' and picking.backorder_id:
		continue

            if picking.state == 'done':
                continue

            if picking.state == 'cancel':
		picking.action_back_to_draft()

            if picking.state == 'draft':
                picking_obj.action_confirm(cr, uid, [picking.id], context=context)

            if picking.state != 'assigned':
                picking_obj.force_assign(cr, uid, [picking.id])

            picking.do_transfer()
	    cr.commit()
            picking_obj.write(cr, uid, [picking.id], {'sw_exp': False, 'sw_pre_exp': False})

        return True


    def mage_status_pending(self, cr, uid, sale, context=None):
        """
        Put the order on hold
        """

        picking_obj = self.pool.get('stock.picking')

        #if the order is already confirmed then cancel all of the pickings and reset them to draft
	print 'SALE NAME', sale.name
        if sale.state == 'done':
            #cannot hold a done order!
            return True

        if sale.state == 'cancel':
            #Reset te state to draft
            sale.state = 'draft'

        if sale.picking_ids:
            for picking in sale.picking_ids:

                if picking.state in ['draft', 'done']:
                    continue

                if picking.state in ['partially_available', 'assigned']:
                    picking_obj.do_unreserve(cr, uid, picking.id)

                if picking.state != 'cancel':
                    picking_obj.action_cancel(cr, uid, picking.id)

                if picking.state == 'cancel':
                    picking.action_back_to_draft()

                picking.sw_exp = False
		picking.sw_pre_exp = False

        return True


    def mage_status_changed(self, cr, uid, sale, mage_status, context=None):
	picking_obj = self.pool.get('stock.picking')
        sale.mage_custom_status = mage_status
        picking_ids = picking_obj.search(cr, uid, [('sale', '=', sale.id)])
        if picking_ids:
            picking_obj.write(cr, uid, picking_ids, {'sw_exp': False, 'sw_pre_exp': False})


    def mage_unhold_order(self, cr, uid, sale, mage_status, context=None):
	if not context:
	    context = None
	picking_obj = self.pool.get('stock.picking')
        if sale.state == 'draft':
            self.confirm_one_order(cr, uid, sale)

        for picking in sale.picking_ids:
            if picking.state == 'draft':
		picking_obj.action_confirm(cr, uid, [picking.id], context=context)
                #picking.action_confirm()
                picking.sw_exp = False
		picking.sw_pre_exp = False

        return;


    def send_error_notification(self, html, recipients_data, sender, subject, from_mail, context=None):
        from email.MIMEMultipart import MIMEMultipart
        from email.MIMEText import MIMEText
        from email.MIMEImage import MIMEImage
        import smtplib
        receivers = []
        to_list = []
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = from_mail

        for person in recipients_data:
            to_list.append("<%s>" % (person['email']))
            receivers.append(person['email'])

        msg['To'] = ', '.join(to_list)
        body = html
        content = MIMEText(body, 'html')
        msg.attach(content)
        try:
            smtpObj = smtplib.SMTP('localhost')
            smtpObj.sendmail(sender, receivers, msg.as_string())
        except Exception, e:
            print 'THERE WAS EXCEPTION', e

        return True
