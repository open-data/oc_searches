import datetime
from datetime import tzinfo
from django.http import HttpRequest
import pytz
from search.models import Search, Field, Code
from SolrClient2 import SolrResponse


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
    # Fix bad data
    if format != "NTR" and 'disclosure_group' in csv_record:
        if csv_record['disclosure_group'] == "SLE - Senior Level Employees":
            csv_record['disclosure_group'] = "SLE"
        if csv_record['disclosure_group'] == "Minister":
            csv_record['disclosure_group'] = "MPSES"
        if csv_record['disclosure_group'] == "Senior DFO Employee":
            csv_record['disclosure_group'] = "SLE"
    return True,  csv_record


MONTH_MAP = {
    "01": 1,
    "02": 2,
    "03": 3,
    "04": 4,
    "05": 5,
    "06": 6,
    "07": 7,
    "08": 8,
    "09": 9,
    "10": 10,
    "11": 11,
    "12": 12
}

def load_csv_record(csv_record: dict, solr_record: dict, search: Search, fields: dict, codes: dict, format: str):


    if format != "NTR":
        solr_record['year'] = solr_record['start_date'][0:4]
        if not csv_record['guest_attendees']:
            solr_record['guest_attendees'] = '0'
        if not csv_record['employee_attendees']:
            solr_record['employee_attendees'] = '0'
        if not csv_record['total']:
            solr_record['total'] = float(0.0)
        if solr_record['total'] == 0:
            solr_record['total_en'] = "0.00"
            solr_record['total_fr'] = "0,00"

        # Set a total facet value
        if float(solr_record['total']) < 250:
            solr_record["total_range"] = "0"
            solr_record["total_range_en"] = codes["total_range"]["0"].label_en
            solr_record["total_range_fr"] = codes["total_range"]["0"].label_fr
        elif 250 <= float(solr_record['total']) < 500:
            solr_record["total_range"] = "1"
            solr_record["total_range_en"] = codes["total_range"]["1"].label_en
            solr_record["total_range_fr"] = codes["total_range"]["1"].label_fr
        elif 500 <= float(solr_record['total']) < 1000:
            solr_record["total_range"] = "2"
            solr_record["total_range_en"] = codes["total_range"]["2"].label_en
            solr_record["total_range_fr"] = codes["total_range"]["2"].label_fr
        elif 1000 <= float(solr_record['total']) < 5000:
            solr_record["total_range"] = "3"
            solr_record["total_range_en"] = codes["total_range"]["3"].label_en
            solr_record["total_range_fr"] = codes["total_range"]["3"].label_fr
        elif 5000 <= float(solr_record['total']) < 25000:
            solr_record["total_range"] = "4"
            solr_record["total_range_en"] = codes["total_range"]["4"].label_en
            solr_record["total_range_fr"] = codes["total_range"]["4"].label_fr
        elif float(solr_record['total']) >= 25000:
            solr_record["total_range"] = "5"
            solr_record["total_range_en"] = codes["total_range"]["5"].label_en
            solr_record["total_range_fr"] = codes["total_range"]["5"].label_fr
    else:
        solr_record["start_date"] = datetime.datetime(int(csv_record["year"]), MONTH_MAP[csv_record["month"]], 1, 0, 0, 0, 0, tzinfo=pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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
