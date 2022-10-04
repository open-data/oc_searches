from babel.numbers import parse_decimal, NumberFormatError
from datetime import datetime, timezone
from django.http import HttpRequest
import logging
from search.models import Search, Field, Code
from SolrClient import SolrResponse


MAX_YEAR = 9999
logger = logging.getLogger(__name__)


def get_dollar_range(dollar_amount: float):
    """
    Given a text string, convert to a float and returns a code value for the amendment_value_range code field.
    """
    return_code = "-"
    if dollar_amount:
        try:
            if dollar_amount < 0:
                return_code = '00'
            elif dollar_amount < 10000:
                return_code = '01'
            elif 10000 <= dollar_amount < 25000:  # lgtm [py/redundant-comparison]
                return_code = '02'
            elif 25000 <= dollar_amount < 100000:  # lgtm [py/redundant-comparison]
                return_code = '03'
            elif 100000 <= dollar_amount < 1000000:  # lgtm [py/redundant-comparison]
                return_code = '04'
            elif 1000000 <= dollar_amount < 5000000:  # lgtm [py/redundant-comparison]
                return_code = '05'
            else:
                return_code = '06'
        except NumberFormatError:
            logger.warning("Error converting dollar amount to float: {}".format(dollar_amount))
            pass
    return return_code


def plugin_api_version():
    return 1.1


def pre_search_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_query


def post_search_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_response


def pre_record_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_query


def post_record_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_response


def pre_export_solr_query(solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list):
    return solr_query


def post_export_solr_query(solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list):
    return solr_response


def pre_mlt_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, record_is: str):
    return context, solr_query


def post_mlt_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, record_ids: str):
    return context, solr_response


def filter_csv_record(csv_record,search: Search, fields: dict, codes: dict, format: str):
    if format != 'NTR':

        if not csv_record['agreement_type_code']:
            csv_record['agreement_type_code'] = '0'
        else:
            # Do some data cleanup on the Agreement Type Code
            if str(csv_record['agreement_type_code']).strip() == 'O' or str(csv_record['agreement_type_code']).strip() == '00':
                csv_record['agreement_type_code'] = '0'
            if csv_record['agreement_type_code'][0:1] == "0":
                csv_record['agreement_type_code'] = '0'
            if csv_record['agreement_type_code'] == 'A,R':
                csv_record['agreement_type_code'] = 'AR'
            if csv_record['agreement_type_code'] == 'AIT':
                csv_record['agreement_type_code'] = 'I'
            if csv_record['agreement_type_code'] == '1':
                csv_record['agreement_type_code'] = 'I'
            if csv_record['agreement_type_code'].startswith('?'):
                csv_record['agreement_type_code'] = ''
            csv_record['agreement_type_code'] = csv_record['agreement_type_code'].strip()

        # Combine all crown owned exemptions into one
        if csv_record['intellectual_property'].startswith('A'):
            csv_record['intellectual_property'] = 'A_'

        if csv_record['article_6_exceptions'].startswith('?'):
            csv_record['article_6_exceptions'] = ''

        if csv_record['award_criteria'][0:1] == "0":
            csv_record['award_criteria'] = '0'
        if csv_record['award_criteria'][0:1] == "?":
            csv_record['award_criteria'] = ''

        if csv_record['trade_agreement_exceptions'] not in codes['trade_agreement_exceptions'] and csv_record['trade_agreement_exceptions'] != '':
            logger.warning('Unknown Trade Agreement Exceptions code: %s for %s,%s', csv_record['trade_agreement_exceptions'],
                           csv_record['owner_org'], csv_record['reference_number'])
            csv_record['trade_agreement_exceptions'] = ''

        if csv_record['country_of_vendor'].lower() not in codes['country_of_vendor'] and csv_record['country_of_vendor'] != '':
            logger.warning('Unknown Country of Vendor code: %s for %s,%s', csv_record['country_of_vendor'],
                           csv_record['owner_org'], csv_record['reference_number'])
            csv_record['country_of_vendor'] = ''

    return True,  csv_record


def load_csv_record(csv_record: dict, solr_record: dict, search: Search, fields: dict, codes: dict, format: str):
    if format == 'NTR':
        solr_record['id'] = f"{csv_record['owner_org']},{csv_record['reporting_period']}"

    else:
        solr_record['format'] = 'DEFAULT'
        if not solr_record['land_claims']:
            solr_record['land_claims'] = '__'
        if solr_record['amendment_value']:
            solr_record['amendment_value_range'] = get_dollar_range(solr_record['amendment_value'])
        if solr_record['original_value']:
            solr_record['original_value_range'] = get_dollar_range(solr_record['original_value'])
        if solr_record['contract_value']:
            solr_record['contract_value_range'] = get_dollar_range(solr_record['contract_value'])

        # Convert date fields to Solr date fields
        working_year = MAX_YEAR
        if csv_record['contract_period_start']:
            contract_period_start_date = datetime.strptime(csv_record['contract_period_start'], '%Y-%m-%d')
            solr_record['contract_period_start'] = contract_period_start_date.strftime('%Y-%m-%dT00:00:00Z')
            working_year = contract_period_start_date.year
        if csv_record['delivery_date']:
            delivery_date = datetime.strptime(csv_record['delivery_date'], '%Y-%m-%d')
            solr_record['delivery_date'] = delivery_date.strftime('%Y-%m-%dT00:00:00Z')
        if csv_record['contract_date']:
            contract_date = datetime.strptime(csv_record['contract_date'], '%Y-%m-%d')
            solr_record['contract_date'] = contract_date.strftime('%Y-%m-%dT00:00:00Z')

        # Expand the Agreement Type Code to their lookup values
        atc = solr_record['agreement_type_code'].lower()
        if atc in codes['agreement_type_code']:
            ta_en = []
            ta_fr = []

            lookup_values = codes['agreement_type_code'][solr_record['agreement_type_code'].lower()].lookup_codes_default.split(',')

            if codes['agreement_type_code'][atc].lookup_date_field:
                # For now we assume all tests are Lest Than comparing dates
                comparison_date = datetime.strptime(csv_record[codes['agreement_type_code'][atc].lookup_date_field], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                if comparison_date < codes['agreement_type_code'][atc].lookup_date:
                    lookup_values = codes['agreement_type_code'][atc].lookup_codes_conditional.split(',')
            for v in lookup_values:
                ta_en.append(codes['agreement_type_code'][v.lower()].label_en)
                ta_fr.append(codes['agreement_type_code'][v.lower()].label_fr)
            solr_record['trade_agreement_en'] = ta_en
            solr_record['trade_agreement_fr'] = ta_fr

        # Handle older aboriginal record codes
        if working_year < 2022 and csv_record['agreement_type_code'] == 'A':
            solr_record['indigenous_business_excluding_psib'] = 'Y'
            solr_record['lands_claims'] = '-'

        if working_year < 2022 and csv_record['agreement_type_code'] == 'B':
            solr_record['indigenous_business_excluding_psib'] = '-'
            solr_record['lands_claims'] = 'Y'

        if working_year < 2022 and csv_record['agreement_type_code'] == 'BA':
            solr_record['indigenous_business_excluding_psib'] = '-'
            solr_record['lands_claims'] = '-'

        if not csv_record['instrument_type']:
            solr_record['instrument_type'] = ''

    return solr_record

# Version 1.1 Methods

def pre_render_search(context: dict, template: str, request: HttpRequest, lang: str, search: Search, fields: dict, codes: dict):
    """
    If required, make changes to the context before rendering the search page or modify the template name
    :param context: the Django view context to be used
    :param template: the default name of the  template to be rendered
    :param request: the HTTP request object
    :param lang: the language of the page being rendered
    :param search: the application search object
    :param fields: the application field objects
    :param codes: the application code objects to be used
    :return: context object, and the template name
    """
    return context, template

def pre_render_record(context: dict, template: str, request: HttpRequest, lang: str, search: Search, fields: dict, codes: dict):
    """
    If required, make changes to the context before rendering the record page or modify the template name
    :param context: the Django view context to be used
    :param template: the default name of the  template to be rendered
    :param request: the HTTP request object
    :param lang: the language of the page being rendered
    :param search: the application search object
    :param fields: the application field objects
    :param codes: the application code objects to be used
    :return: context object, and the template name
    """
    return context, template
