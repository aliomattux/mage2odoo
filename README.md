Mage2Odoo - Turn Key Solution for Magento
---------

Turn key solution for Magento. 
-----------------------------

Tested working with Odoo 8.0 Revision 04b252b72c3bb5568f002e05d2fa889a1b4aae90


General Requirements
--------------------

Requires Python libraries
-------------------------

PIL

pycountry

https://github.com/aliomattux/magento


Required Magento Module
-----------------------
https://github.com/aliomattux/Openobject_OpenobjectConnector


Requires Odoo Modules
--------------------
https://github.com/aliomattux/payment_method

delivery - Odoo Module

https://github.com/aliomattux/stock_package

https://github.com/aliomattux/product_sku_upc


Recommended Server patches
--------------------------

Repo: https://github.com/aliomattux/server_patches

Login Patch

This patch will prevent a frequent concurrent access update.
All scheduled jobs in Mage2Odoo run on the superuser account. If any one person logs in or clicks any button, performs any action,
The server will cancel the currenly running job because of a SELECT FOR UPDATE NOWAIT hack. This method def login also writes the last logged in
timestamp, which can cause cascading write concurrency issues.

Sale Order Line Patch

There is a bug in method create in sale module for sale_order_line class. The onchange method for product will reset all default values
if the field 'type' is not specified in the vals. This field does not exist so it will always do this. Remove this field from the methd

Updating relational many2many tables

The ORM will currently iterate over each item and execute a delete statement which is exponentially slow. This patch does a single DELETE FROM query
which will save serious time when performing large batching operations


Optional Addons
---------------

https://github.com/aliomattux/mage2odoo_sale_automation

This module can automate synchronizing historical data. It can also auto pay/auto deliver sales orders that are paid/delivered in Magento

https://github.com/aliomattux/mage2odoo_cart_shippping_quote

This module will allow you to take your Odoo quote and get a shipping quote for every carrier you offer on Magento.
You can add the shipping cost to your Odoo quote

https://github.com/aliomattux/mage2odoo_authorizenet

This module in addition to our Authorize.net module will allow you to process credit card transactions in Odoo
Supports full/partial authorization and capture in Odoo. *Only supports secured payment tokens.

https://github.com/aliomattux/mage2odoo_operations

This module adds functionality to the delivery order object and adds information on the deliveries about your Magento Store

https://github.com/aliomattux/mage2odoo_salesman

Amasty Salesman module

This module will import salesman to Odoo when assigned to a sales order in Magento

https://github.com/aliomattux/mage2odoo_custom_shipping_account

This module adds functionality to the sales order similar to a custom Magento module that allows you to specify a customers shipping account for FedEx/UPS

Donate to our project
---------------------

If you are interested in donating, or are interesting in funding enhancements please contact me kyle.waid@gcotech.com
