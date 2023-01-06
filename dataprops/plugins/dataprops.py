from django.conf import settings
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

    # The updates for the S.D. are represented in Solr by separate English and French lists For ease of use in the
    # template, combine these fields into a single English and French list.

    for doc in context['docs']:
        status_updates = []
        if "status_update_reason" in doc:
            if lang == 'fr':
                for i, update_date in enumerate(doc['status_update_dates_fra']):
                    update_reason = doc['status_update_reason_fr'][i]
                    update_comment = doc['status_update_comments_fr'][i]
                    status_updates.append({'date': update_date, "reason": update_reason, "comment": update_comment})
            else:
                for i, update_date in enumerate(doc['status_update_dates_eng']):
                    update_reason = doc['status_update_reason_en'][i]
                    update_comment = doc['status_update_comments_en'][i]
                    status_updates.append({'date': update_date, "reason": update_reason, "comment": update_comment})
        doc["status_updates"] = status_updates

    context['votes_base_en'] = settings.SD_VOTES_BASE_EN
    context['votes_base_fr'] = settings.SD_VOTES_BASE_FR
    context['comments_base_en'] = settings.SD_COMMENTS_BASE_EN
    context['comments_base_fr'] = settings.SD_COMMENTS_BASE_FR

    if lang == 'fr':
        context['search_title'] = f"Jeux de données proposés : {context['docs'][0]['title_fr']}"
    else:
        context['search_title'] = f"Suggested Dataset: {context['docs'][0]['title_en']}"

    return context, template
