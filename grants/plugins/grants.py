from babel.numbers import NumberFormatError, parse_decimal, format_currency
from datetime import date
from django.http import HttpRequest
from search.models import Search, Field, Code
from SolrClient import SolrResponse


def _set_bilingual_field(field_name: str, field_value: str, solr_record: list):
    values = field_value.split('|')
    if len(values) == 1:
        solr_record['{0}_en'.format(field_name)] = field_value
        solr_record['{0}_fr'.format(field_name)] = field_value
    else:
        solr_record['{0}_en'.format(field_name)] = values[0].strip()
        solr_record['{0}_fr'.format(field_name)] = values[1].strip()
    return solr_record


def plugin_api_version():
    return 1.1


def pre_search_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    # Only show the latest grants and contributions, not the amendments
    solr_query['hl.q'] = solr_query['q']
    solr_query['q'] = '{0} AND (amendment_number:"current" OR amendment_number:"-")'.format(solr_query['q'])
    return context, solr_query


def post_search_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_response


def pre_record_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    if request.get_raw_uri().endswith('?amendments'):
        id_parts = record_ids.split(",")
        if len(id_parts) == 3:
            solr_query['q'] = 'ref_number:"{0}" AND owner_org:"{1}"'.format(id_parts[1], id_parts[0])
            solr_query['sort'] = 'amendment_number desc'
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
    # This is a bunch of data clean up code needed as of March 2022
    if format != "NTR":
        if csv_record['recipient_province'].lower() not in codes['recipient_province']:
            csv_record['recipient_province'] = 'zz'
        if csv_record['agreement_type'].lower() not in codes['agreement_type']:
            if csv_record['agreement_type'] and csv_record['agreement_type'][0].lower() in codes['agreement_type']:
                csv_record['agreement_type'] = csv_record['agreement_type'][0].upper()
    return True,  csv_record


def load_csv_record(csv_record: dict, solr_record: dict, search: Search, fields: dict, codes: dict, format: str):

    if format == 'NTR':
        solr_record['has_amendments'] = "0"
        if len(csv_record['fiscal_year']) > 4:
            try:
                year = int(csv_record['fiscal_year'][0:4])
                if csv_record['quarter'] == 'Q1':
                    start_date = date(year, 4, 1)
                elif csv_record['quarter'] == 'Q2':
                    start_date = date(year, 7, 1)
                elif csv_record['quarter'] == 'Q3':
                    start_date = date(year, 10, 1)
                elif csv_record['quarter'] == 'Q4':
                    start_date = date(year + 1, 1, 1)
                solr_record['agreement_start_date'] = start_date.strftime('%Y-%m-%d')
                solr_record['year'] = start_date.year
                solr_record['month'] = start_date.month
            except ValueError:
                pass
    else:
        solr_record['format_en'] = 'Grants and Contributions'
        solr_record['format_fr'] = 'Subventions et contributions'
        try:
            agreement_value = parse_decimal(csv_record['agreement_value'].replace('$', '').replace(',', ''),
                                            locale='en')
            # Set a value range
            if agreement_value < 0:
                solr_record['agreement_value_range_en'] = '(a) Negative'
                solr_record['agreement_value_range_fr'] = '(a) negatif'
            elif agreement_value < 10000:
                solr_record['agreement_value_range_en'] = '(b) Less than $10,000'
                solr_record['agreement_value_range_fr'] = '(b) moins de 10 000 $'
            elif 10000 <= agreement_value < 25000:
                solr_record['agreement_value_range_en'] = '(c) $10,000 - $25,000'
                solr_record['agreement_value_range_fr'] = '(c) de 10 000 $ à 25 000 $'
            elif 25000 <= agreement_value < 100000:
                solr_record['agreement_value_range_en'] = '(d) $25,000 - $100,000'
                solr_record['agreement_value_range_fr'] = '(d) de 25 000 $ à 100 000 $'
            elif 100000 <= agreement_value < 1000000:
                solr_record['agreement_value_range_en'] = '(e) $100,000 - $1,000,000'
                solr_record['agreement_value_range_fr'] = '(e) de 100 000 $ à 1 000 000 $'
            elif 1000000 <= agreement_value < 5000000:
                solr_record['agreement_value_range_en'] = '(f) $1,000,000 - $5,000,000'
                solr_record['agreement_value_range_fr'] = '(f) de 1 000 000 $ à 5 000 000 $'
            else:
                solr_record['agreement_value_range_en'] = '(g) More than $5,000,000'
                solr_record['agreement_value_range_fr'] = '(g) plus de cinq millions $'

        except NumberFormatError:
            pass

        # Flag the record for amendments
        if csv_record['amendment_number'] != "current":
            solr_record['has_amendments'] = "1"
        elif csv_record['amendment_number'] == "current" and csv_record['amendment_date'] != "":
            solr_record['has_amendments'] = "1"
        else:
            solr_record['has_amendments'] = "0"

        # The coverage field is bilingual
        if 'coverage' in csv_record and csv_record['coverage']:
            solr_record = _set_bilingual_field('coverage', csv_record['coverage'], solr_record)
        if 'recipient_legal_name' in csv_record and csv_record['recipient_legal_name']:
            solr_record = _set_bilingual_field('recipient_legal_name', csv_record['recipient_legal_name'], solr_record)
        if 'recipient_operating_name' in csv_record and csv_record['recipient_operating_name']:
            solr_record = _set_bilingual_field('recipient_operating_name', csv_record['recipient_operating_name'], solr_record)
        if 'research_organization_name' in csv_record and csv_record['research_organization_name']:
            solr_record = _set_bilingual_field('research_organization_name', csv_record['research_organization_name'], solr_record)
        if 'recipient_city' in csv_record and csv_record['recipient_city']:
            solr_record = _set_bilingual_field('recipient_city', csv_record['recipient_city'], solr_record)

        # Make the agreement number searchable
        solr_record['agreement_number_text'] = solr_record['agreement_number']

    return solr_record


def pre_render_search(context: dict, template: str, request: HttpRequest, lang: str, search: Search, fields: dict, codes: dict):
    return context, template


def pre_render_record(context: dict, template: str, request: HttpRequest, lang: str, search: Search, fields: dict, codes: dict):
    if request.get_raw_uri().endswith('?amendments'):
        context['amendments'] = True
    else:
        context['amendments'] = False
    return context, template
