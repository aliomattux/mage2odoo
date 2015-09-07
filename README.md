Mage2Odoo
---------

Turn key solution for Magento. Tested working with Odoo 8.0 Revision 04b252b72c3bb5568f002e05d2fa889a1b4aae90
-----------------------------


General Requirements
--------------------

Requires Python libraries
-------------------------

PIL

pycountry

magento (Do not use PIP version as it is out of date. Download directly from Github)


Requires Odoo Modules
--------------------
payment_method

delivery

stock_package

product_upc_sku


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
