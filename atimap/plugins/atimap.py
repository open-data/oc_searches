from django.http import HttpRequest
from search.models import Search, Field, Code
from SolrClient2 import SolrResponse


def plugin_api_version():
    return 1.1

def circle_progress_bar_offset(value: int, total: int):
    if value == 0:
        return 360
    else:
        return 360 - round(value * 360 / total)


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
    #csv_record['status'] = csv_record['status'].upper()
    csv_record['target_date'] = csv_record['target_date'].strip().replace(" ", "_")
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
    if context['total_hits'] == 0:
        context['ip_offset'] = 360
        context['ns_offset'] = 360
        context['co_offset'] = 360
        context['on_offset'] = 360
        context['ip_num'] = 0
        context['ns_num'] = 0
        context['co_num'] = 0
        context['on_num'] = 0
        context['IP_EC_list'] = ()
        context['NS_NC_list'] = ()
        context['CP_RL_list'] = ()
        context['ON_CO_list'] = {}

    else:

        context['show_all_results'] = True
        for p in request.GET:
            if p not in ['encoding', 'page', 'sort']:
                context['show_all_results'] = False
                break
        # @TODO Do some better calculations for the circle progress bars on the search page for more accurate rendering

        # The graph at the top or the search page uses non-standard facet counts - when the status facets are selected,
        # the unselected values are automatically set to zero. It is simpler to calculate these numbers here instead of
        # in the template

        if 'status' in request.GET:
            statii = request.GET.getlist('status')
            stati = statii[0].split('|')
            context['ip_offset'] = circle_progress_bar_offset(context['facets']['status']['IP_EC'], context['total_hits']) if 'IP_EC' in stati and 'IP_EC' in context['facets']['status'] else 360
            context['ns_offset'] = circle_progress_bar_offset(context['facets']['status']['NS_NC'], context['total_hits']) if "NS_NC" in stati and 'NS_NC' in context['facets']['status'] else 360
            context['co_offset'] = circle_progress_bar_offset(context['facets']['status']['CP_RL'], context['total_hits']) if "CP_RL" in stati and 'CP_RL' in context['facets']['status'] else 360
            context['on_offset'] = circle_progress_bar_offset(context['facets']['status']['ON_CO'], context['total_hits']) if "ON_CO" in stati and 'ON_CO' in context['facets']['status'] else 360

            context['ip_num'] = context['facets']['status']['IP_EC'] if 'IP_EC' in stati and 'IP_EC' in context['facets']['status'] else 0
            context['ns_num'] = context['facets']['status']['NS_NC'] if "NS_NC" in stati and 'NS_NC' in context['facets']['status'] else 0
            context['co_num'] = context['facets']['status']['CP_RL'] if "CP_RL" in stati and 'CP_RL' in context['facets']['status'] else 0
            context['on_num'] = context['facets']['status']['ON_CO'] if "ON_CO" in stati and "ON_CO" in context['facets']['status'] else 0

            for s in ['IP_EC', 'NS_NC', 'CP_RL', 'ON_CO']:
                stati2 = stati.copy()
                if s in stati:
                    stati2.remove(s)
                else:
                    # We do not want to show any links when clicking on the status would result in no change or zero results
                    if s in context['facets']['status'] and context['facets']['status'][s] > 0:
                        stati2.append(s)
                    elif stati == stati2:
                        stati2 = ()
                context[s + "_list"] = "|".join(stati2)

        else:
            context['ip_offset'] = circle_progress_bar_offset(context['facets']['status']['IP_EC'], context['total_hits']) if 'IP_EC' in context['facets']['status'] else 360
            context['ns_offset'] = circle_progress_bar_offset(context['facets']['status']['NS_NC'], context['total_hits']) if "NS_NC" in context['facets']['status'] else 360
            context['co_offset'] = circle_progress_bar_offset(context['facets']['status']['CP_RL'], context['total_hits']) if "CP_RL" in context['facets']['status'] else 360
            context['on_offset'] = circle_progress_bar_offset(context['facets']['status']['ON_CO'], context['total_hits']) if "ON_CO" in context['facets']['status'] else 360
            context['ip_num'] = context['facets']['status']['IP_EC'] if 'IP_EC' in context['facets']['status'] else 0
            context['ns_num'] = context['facets']['status']['NS_NC'] if "NS_NC" in context['facets']['status'] else 0
            context['co_num'] = context['facets']['status']['CP_RL'] if "CP_RL" in context['facets']['status'] else 0
            context['on_num'] = context['facets']['status']['ON_CO'] if "ON_CO" in context['facets']['status'] else 0

            for s in ['IP_EC', 'NS_NC', 'CP_RL', 'ON_CO']:
                if s in context['facets']['status'] and context['facets']['status'][s] > 0:
                    context[s.replace(" ", "_") + "_list"] = s
                else:
                    context[s.replace(" ", "_") + "_list"] = ()


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
