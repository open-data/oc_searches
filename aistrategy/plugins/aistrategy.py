from django.http import HttpRequest
from search.models import Search, Field, Code
from SolrClient import SolrResponse


def plugin_api_version():
    return 1.1


def circle_progress_bar_offset(value: int, total: int):
    if value == 0:
        return 360
    else:
        return 360 - round(value * 360 / total)
    

def pre_search_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    solr_query['group'] = True
    solr_query['group.field'] = 'ref_number'
    solr_query['group.sort'] = 'reporting_period desc'
    solr_query['group.limit'] = 1
    return context, solr_query


def post_search_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_response


def pre_record_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    ref_number = solr_query['q'].split(':')[1].split(",")[1].strip("\"'")
    solr_query['q'] = f"ref_number:{ref_number}"
    solr_query['sort'] = "reporting_period desc"
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
    solr_record['activity_eng'] = codes['activity'][csv_record['activity'].lower()].label_en
    solr_record['activity_eng'] = codes['activity'][csv_record['activity'].lower()].label_fr
    solr_record['key_action_eng'] = codes['key_action'][csv_record['key_action'].lower()].label_en
    solr_record['key_action_fra'] = codes['key_action'][csv_record['key_action'].lower()].label_fr
    solr_record['sub_action_eng'] = codes['sub_action'][csv_record['sub_action'].lower()].label_en
    solr_record['sub_action_fra'] = codes['sub_action'][csv_record['sub_action'].lower()].label_fr            
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
        context['ip_num'] = 0
        context['ns_num'] = 0
        context['co_num'] = 0
        context['IP_list'] = ()
        context['NS_list'] = ()
        context['CO_list'] = ()

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
            context['ip_offset'] = circle_progress_bar_offset(context['facets']['status']['IP'], context['total_hits']) if 'IP' in stati and 'IP' in context['facets']['status'] else 360
            context['ns_offset'] = circle_progress_bar_offset(context['facets']['status']['NS'], context['total_hits']) if "NS" in stati and 'NS' in context['facets']['status'] else 360
            context['co_offset'] = circle_progress_bar_offset(context['facets']['status']['CO'], context['total_hits']) if "CO" in stati and 'CO' in context['facets']['status'] else 360

            context['ip_num'] = context['facets']['status']['IP'] if 'IP' in stati and 'IP' in context['facets']['status'] else 0
            context['ns_num'] = context['facets']['status']['NS'] if "NS" in stati and 'NS' in context['facets']['status'] else 0
            context['co_num'] = context['facets']['status']['CO'] if "CO" in stati and 'CO' in context['facets']['status'] else 0

            for s in ['IP', 'NS', 'CO']:
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
            context['ip_offset'] = circle_progress_bar_offset(context['facets']['status']['IP'], context['total_hits']) if 'IP' in context['facets']['status'] else 360
            context['ns_offset'] = circle_progress_bar_offset(context['facets']['status']['NS'], context['total_hits']) if "NS" in context['facets']['status'] else 360
            context['co_offset'] = circle_progress_bar_offset(context['facets']['status']['CO'], context['total_hits']) if "CO" in context['facets']['status'] else 360
            context['ip_num'] = context['facets']['status']['IP'] if 'IP' in context['facets']['status'] else 0
            context['ns_num'] = context['facets']['status']['NS'] if "NS" in context['facets']['status'] else 0
            context['co_num'] = context['facets']['status']['CO'] if "CO" in context['facets']['status'] else 0

            for s in ['IP', 'NS', 'CO']:
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
