from openerp.osv import osv
from openerp.tools.translate import _
import pycountry


class ResCountry(osv.osv):
    _inherit = 'res.country'

    def search_using_magento_code(self, cursor, user, code, context):
        """
        Searches for country with given magento code.

        :param cursor: Database cursor
        :param user: ID of current user
        :param code: ISO code of country
        :param context: Application context
        :return: Browse record of country if found else raises error
        """
        country_ids = self.search(
            cursor, user, [('code', '=', code.upper())], context=context
        )

        if not country_ids:
            raise osv.except_osv(
                _('Not Found!'),
                _('Country with ISO code %s does not exists.' % code)
            )

        country = self.browse(
            cursor, user, country_ids[0], context=context
        )

        return country


class ResCountryState(osv.Model):
    _inherit = 'res.country.state'

    def find_or_create_using_magento_region(
        self, cursor, user, country, region, context
    ):
        """
        Looks for the state whose `region` is sent by magento in `country`
        If state already exists, return that else create a new one and
        return

        :param cursor: Database cursor
        :param user: ID of current user
        :param country: Browse record of country
        :param region: Name of state from magento
        :param context: Application context
        :return: Browse record of record created/found
        """
        state = self.find_using_magento_region(
            cursor, user, country, region, context
        )
        if not state:
            state = self.create_using_magento_region(
                cursor, user, country, region, context
            )

        return state


    def find_using_magento_region(
        self, cursor, user, country, region, context
    ):
        """
        Looks for the state whose `region` is sent by magento
        If state already exists, return that

        :param cursor: Database cursor
        :param user: ID of current user
        :param country: Browse record of country
        :param region: Name of state from magento
        :param context: Application context
        :return: Browse record of record found
        """
        state_ids = self.search(
            cursor, user, [
                ('name', 'ilike', region),
                ('country_id', '=', country.id),
            ], context=context
        )

        return state_ids and self.browse(
            cursor, user, state_ids[0], context=context
        ) or None


    def create_using_magento_region(
        self, cursor, user, country, region, context
    ):
        """
        Creates state for the region sent by magento

        :param cursor: Database cursor
        :param user: ID of current user
        :param country: Browse record of country
        :param region: Name of state from magento
        :param context: Application context
        :return: Browse record of record created
        """
        code = None
        try:
            for subdivision in pycountry.subdivisions.get(
                    country_code=country.code):
                if subdivision.name.upper() == region.upper():
                    code = ''.join(list(region)[:3]).upper()
                    break
            if not code:
                if country.code == 'US':
                    code = 'APO'
                else:
                    code = ''.join(list(region)[:3]).upper()
        except KeyError:
            raise osv.except_osv(
                _('Country Not Found!'),
                _('No country found with code %s' % country.code)
            )
        finally:
	    #TODO: are all 3 of these fields required?
	    #We must detect in advance if create() will fail
	    #Because Odoo cannot handle a try/catch around creation error
	    if region and country and code:
                state_id = self.create(
                    cursor, user, {
                        'name': region,
                        'country_id': country.id,
                        'code': code,
                    }, context=context
                )
	    else:
		if not region:
			error = 'There is no State Mapping. This order cannot import'
		elif not country:
		    error = 'There is no Country. This order cannot import'
		else:
		    error = 'There is no State Code. This order cannot import'

                raise osv.except_osv(
                    _('Address Country/State Mapping Error'),
                    _(error)
                )
        return self.browse(cursor, user, state_id, context=context)
