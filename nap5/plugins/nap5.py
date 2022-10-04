from django.http import HttpRequest
from search.models import Search, Field, Code
from SolrClient import SolrResponse


# --custom method

def circle_progress_bar_offset(value: int, total: int):
    if value == 0:
        return 360
    else:
        return 360 - round(value * 360 / total)


def plugin_api_version():
    return 1.1


def pre_search_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):

    solr_query['group'] = True
    solr_query['group.field'] = 'indicators'
    solr_query['group.limit'] = 1
    solr_query['group.sort'] = 'reporting_period_no desc'
    solr_query['group.facet'] = True
    solr_query['group.main'] = True
    solr_query['group.truncate'] = True
    #solr_query['fq'].insert(0, "{!collapse field=indicators max=reporting_period_no size=1}")
    #solr_query['fq'].append("{!collapse field=indicators}")
    #solr_query['expand'] = False

    solr_query['q'] = f'{solr_query["q"]} AND (is_latest:"T")'

    return context, solr_query


def post_search_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_response


def pre_record_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_id: str):
    id_parts = record_id.split(",")
    if len(id_parts) > 1:
        solr_query['q'] = 'indicators:"{0}"'.format(id_parts[1])
        solr_query['sort'] = 'reporting_period desc'

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
    redundant_fields = ['indicator_en', 'indicator_fr', 'indicator_due_date', 'indicator_deadline_en',
                        'indicator_deadline_fr', 'indicator_lead_dept', 'indicator_s4d']
    # This is redundant if the nap5_preprocess_csv.py command is run, but is hear as a precaution
    for f in redundant_fields:
        if f in csv_record:
            del csv_record[f]
    return True,  csv_record


def load_csv_record(csv_record: dict, solr_record: dict, search: Search, fields: dict, codes: dict, format: str):

    if solr_record['indicators_en']:
        solr_record['indicators_eng'] = f'{solr_record["indicators"]} - {solr_record["indicators_en"]}'
    if solr_record['indicators_fr']:
        solr_record['indicators_fra'] = f'{solr_record["indicators"]} - {solr_record["indicators_fr"]}'
    solr_record['milestones_eng'] = solr_record['milestones_en'] if solr_record['milestones_en'] else '-'
    solr_record['milestones_fra'] = solr_record['milestones_fr'] if solr_record['milestones_fr'] else '-'
    indicator = csv_record['indicators'].lower()
    if indicator in codes['indicators']:
        if codes['indicators'][indicator].extra_03 == "True":
            solr_record['s4d'] = "y"
            solr_record['s4d_en'] = codes['s4d']['y'].label_en
            solr_record['s4d_fr'] = codes['s4d']['y'].label_fr
        else:
            solr_record['s4d'] = "n"
            solr_record['s4d_en'] = codes['s4d']['n'].label_en
            solr_record['s4d_fr'] = codes['s4d']['n'].label_fr
        solr_record['due_date'] = codes['indicators'][indicator].extra_01
        if solr_record['due_date'] in codes['due_date']:
            solr_record['due_date_en'] = codes['due_date'][solr_record['due_date']].label_en
            solr_record['due_date_fr'] = codes['due_date'][solr_record['due_date']].label_fr
        else:
            solr_record['due_date_en'] = solr_record['due_date']
            solr_record['due_date_fr'] = solr_record['due_date']
        solr_record['deadline_en'] = codes['indicators'][indicator].extra_04_en
        solr_record['deadline_fr'] = codes['indicators'][indicator].extra_04_fr
        solr_record['reporting_period_no'] = int(csv_record['reporting_period'][0:4] + csv_record['reporting_period'][5:7])
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
    # If there is no search text and no facets, then hide the results message

    if context['total_hits'] == 0:
        context['c_offset'] = 360
        context['sp_offset'] = 360
        context['lp_offset'] = 360
        context['ns_offset'] = 360
        context['c_num'] = 0
        context['sp_num'] = 0
        context['lp_num'] = 0
        context['ns_num'] = 0
        context['C_list'] = ()
        context['SP_list'] = ()
        context['LP_list'] = ()
        context['NS_list'] = ()
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
            context['c_offset'] = circle_progress_bar_offset(context['facets']['status']['C'], context['total_hits']) if "C" in stati else 360
            context['sp_offset'] = circle_progress_bar_offset(context['facets']['status']['SP'], context['total_hits']) if "SP" in stati else 360
            context['lp_offset'] = circle_progress_bar_offset(context['facets']['status']['LP'], context['total_hits']) if "LP" in stati else 360
            context['ns_offset'] = circle_progress_bar_offset(context['facets']['status']['NS'], context['total_hits']) if "NS" in stati else 360
            context['c_num'] = context['facets']['status']['C'] if "C" in stati else 0
            context['sp_num'] = context['facets']['status']['SP'] if "SP" in stati else 0
            context['lp_num'] = context['facets']['status']['LP'] if "LP" in stati else 0
            context['ns_num'] = context['facets']['status']['NS'] if "NS" in stati else 0
            for s in ['C', 'SP', 'LP', 'NS']:
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
            context['c_offset'] = circle_progress_bar_offset(context['facets']['status']['C'], context['total_hits']) if "C" in context['facets']['status'] else 360
            context['sp_offset'] = circle_progress_bar_offset(context['facets']['status']['SP'], context['total_hits']) if "SP" in context['facets']['status'] else 360
            context['lp_offset'] = circle_progress_bar_offset(context['facets']['status']['LP'], context['total_hits']) if "LP" in context['facets']['status'] else 360
            context['ns_offset'] = circle_progress_bar_offset(context['facets']['status']['NS'], context['total_hits']) if "NS" in context['facets']['status'] else 360
            context['c_num'] = context['facets']['status']['C'] if "C" in context['facets']['status'] else 0
            context['sp_num'] = context['facets']['status']['SP'] if "SP" in context['facets']['status'] else 0
            context['lp_num'] = context['facets']['status']['LP'] if "LP" in context['facets']['status'] else 0
            context['ns_num'] = context['facets']['status']['NS'] if "NS" in context['facets']['status'] else 0
            for s in ['C', 'SP', 'LP', 'NS']:
                if s in context['facets']['status'] and context['facets']['status'][s] > 0:
                    context[s + "_list"] = s
                else:
                    context[s + "_list"] = ()

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
