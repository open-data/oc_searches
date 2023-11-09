from babel.dates import format_date
from datetime import datetime, time, timezone
from dateutil import parser
from dateutil.tz import gettz
from django.http import HttpRequest
from search.models import Search, Field, Code
from SolrClient import SolrResponse


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
    return True,  csv_record


def load_csv_record(csv_record: dict, solr_record: dict, search: Search, fields: dict, codes: dict, format: str):
    if csv_record['ex_completion_dt']:
        cdn_tzinfos = {
            "AST": gettz("Canada/Atlantic"),
            "ADT": -60 * 60 * 3,
            "CST": gettz("Canada/ Central"),
            "CDT": -60 * 60 * 5,
            "EST": gettz("Canada/Eastern"),
            "EDT": -60 * 60 * 4,
            "MST": gettz("Canada/Mountain"),
            "MDT": -60 * 60 * 6,
            "NST": gettz("Canada/Newfoundland"),
            "NDT": int(-60 * 60 * 2.5),
            "PST": gettz("Canada/Pacific"),
            "PDT": -60 * 60 * 7,
            "YST": gettz("Canada/Yukon"),
            "YDT": -60 * 60 * 7
            }

        now_dt = datetime.now()
        default_dt = datetime(now_dt.year, 12, 31, 12, 0, 0, 0, cdn_tzinfos['EST'])
        completion_dt = parser.parse(csv_record['ex_completion_dt'], tzinfos=cdn_tzinfos, default=default_dt)
        solr_record['ex_completion_dt'] = completion_dt.isoformat()
        solr_record['ex_completion_dt_eng'] = format_date(completion_dt, locale='en')
        solr_record['ex_completion_dt_fra'] = format_date(completion_dt, locale='fr')
        sort_period = f'{completion_dt.year}{completion_dt.month:02d}'
        solr_record['ex_completion_period'] = sort_period
        per_field_id = fields['ex_completion_period'].fid
        period_field = Field.objects.get(fid=per_field_id)
        choice, created = Code.objects.get_or_create(code_id=sort_period, field_fid=period_field)
        if created:
            choice.label_en = format_date(completion_dt, "MMM yyyy", locale='en')
            choice.label_fr = format_date(completion_dt, "MMM yyyy", locale='fr')
            choice.save()
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
