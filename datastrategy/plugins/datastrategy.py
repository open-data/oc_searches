# from babel.dates import format_date
# from datetime import datetime, time, timezone
# from dateutil import parser
# from dateutil.tz import gettz
from django.http import HttpRequest
from search.models import Search, Field, Code
from SolrClient2 import SolrResponse


def circle_progress_bar_offset(value: int, total: int):
    if value == 0:
        return 360
    else:
        return 360 - round(value * 360 / total)


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
    if csv_record['priority']:
        y_set = False
        for y in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            if csv_record['priority'].find(y) > -1:
                csv_record['priority'] = y
                y_set = True
                break
        if not y_set:
            csv_record['priority'] = 0
    else:
        csv_record['priority'] = 0

    return True,  csv_record


def load_csv_record(csv_record: dict, solr_record: dict, search: Search, fields: dict, codes: dict, format: str):
    # if csv_record['ex_completion_dt']:
    #     cdn_tzinfos = {
    #         "AST": gettz("Canada/Atlantic"),
    #         "ADT": -60 * 60 * 3,
    #         "CST": gettz("Canada/ Central"),
    #         "CDT": -60 * 60 * 5,
    #         "EST": gettz("Canada/Eastern"),
    #         "EDT": -60 * 60 * 4,
    #         "MST": gettz("Canada/Mountain"),
    #         "MDT": -60 * 60 * 6,
    #         "NST": gettz("Canada/Newfoundland"),
    #         "NDT": int(-60 * 60 * 2.5),
    #         "PST": gettz("Canada/Pacific"),
    #         "PDT": -60 * 60 * 7,
    #         "YST": gettz("Canada/Yukon"),
    #         "YDT": -60 * 60 * 7
    #         }
    #
    #     now_dt = datetime.now()
    #     default_dt = datetime(now_dt.year, 12, 31, 12, 0, 0, 0, cdn_tzinfos['EST'])
    #     completion_dt = parser.parse(csv_record['ex_completion_dt'], tzinfos=cdn_tzinfos, default=default_dt)
    #     solr_record['ex_completion_dt'] = completion_dt.isoformat()
    #     solr_record['ex_completion_dt_eng'] = format_date(completion_dt, locale='en')
    #     solr_record['ex_completion_dt_fra'] = format_date(completion_dt, locale='fr')
    #     sort_period = f'{completion_dt.year}{completion_dt.month:02d}'
    #     solr_record['ex_completion_period'] = sort_period
    #     per_field_id = fields['ex_completion_period'].fid
    #     period_field = Field.objects.get(fid=per_field_id)
    #     choice, created = Code.objects.get_or_create(code_id=sort_period, field_fid=period_field)
    #     if created:
    #         choice.label_en = format_date(completion_dt, "MMM yyyy", locale='en')
    #         choice.label_fr = format_date(completion_dt, "MMM yyyy", locale='fr')
    #         choice.save()

    # Replace the wordy priority text with a simpler code

    solr_record['priority_en'] = f"Year {csv_record['priority']} priority"
    solr_record['priority_fr'] = f"Année {csv_record['priority']} priorité"
    solr_record['id'] = f"{csv_record['action_id']},{csv_record['priority']}"
    return solr_record

# Version 1.1 Methods


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
        context['bl_offset'] = 360
        context['be_offset'] = 360
        context['ip_num'] = 0
        context['ns_num'] = 0
        context['co_num'] = 0
        context['bl_num'] = 0
        context['be_num'] = 0
        context['ip_list'] = ()
        context['ns_list'] = ()
        context['co_list'] = ()
        context['bl_list'] = ()
        context['be_list'] = ()
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
        if request.LANGUAGE_CODE == 'fr':
            if 'action_status_fr' in request.GET:
                statii = request.GET.getlist('action_status_fr')
                stati = statii[0].split('|')
                context['ip_offset'] = circle_progress_bar_offset(context['facets']['action_status_fr']['En cours'], context['total_hits']) if "En cours" in stati and 'En cours' in context['facets']['action_status_fr'] else 360
                context['ns_offset'] = circle_progress_bar_offset(context['facets']['action_status_fr']['Non entamée'], context['total_hits']) if "Pas commencé" in stati and 'Non entamée' in context['facets']['action_status_fr'] else 360
                context['co_offset'] = circle_progress_bar_offset(context['facets']['action_status_fr']['Terminée'], context['total_hits']) if "Terminée" in stati and 'Terminée' in context['facets']['action_status_fr'] else 360
                context['bl_offset'] = circle_progress_bar_offset(context['facets']['action_status_fr']['En pause'], context['total_hits']) if "En pause" in stati and 'En pause' in context['facets']['action_status_fr'] else 360
                context['be_offset'] = circle_progress_bar_offset(context['facets']['action_status_fr']['Behind'], context['total_hits']) if "Behind" in stati and 'Behind' in context['facets']['action_status_fr'] else 360

                context['ip_num'] = context['facets']['action_status_fr']['En cours'] if "En cours" in stati and 'En cours' in context['facets']['action_status_fr'] else 0
                context['ns_num'] = context['facets']['action_status_fr']['Non entamée'] if "Non entamée" in stati and 'Non entamée' in context['facets']['action_status_fr'] else 0
                context['co_num'] = context['facets']['action_status_fr']['Terminée'] if "Terminée" in stati and 'Terminée' in context['facets']['action_status_fr'] else 0
                context['bl_num'] = context['facets']['action_status_fr']['En pause'] if "En pause" in stati and 'En pause' in context['facets']['action_status_fr'] else 0
                context['be_num'] = context['facets']['action_status_fr']['Behind'] if "Behind" in stati and 'Behind' in context['facets']['action_status_fr'] else 0

                for s in ['En cours', 'Non entamée', 'Terminée', 'En pause', 'Behind']:
                    stati2 = stati.copy()
                    if s in stati:
                        stati2.remove(s)
                    else:
                        # We do not want to show any links when clicking on the status would result in no change or zero results
                        if s in context['facets']['action_status_fr'] and context['facets']['action_status_fr'][s] > 0:
                            stati2.append(s)
                        elif stati == stati2:
                            stati2 = ()
                    context[s.replace(" ", "_").replace('é', 'e') + "_list"] = "|".join(stati2)

            else:
                context['ip_offset'] = circle_progress_bar_offset(context['facets']['action_status_fr']['En cours'], context['total_hits']) if "En cours" in context['facets']['action_status_fr'] else 360
                context['ns_offset'] = circle_progress_bar_offset(context['facets']['action_status_fr']['Non entamée'], context['total_hits']) if "Non entamée" in context['facets']['action_status_fr'] else 360
                context['co_offset'] = circle_progress_bar_offset(context['facets']['action_status_fr']['Terminée'], context['total_hits']) if "Terminée" in context['facets']['action_status_fr'] else 360
                context['bl_offset'] = circle_progress_bar_offset(context['facets']['action_status_fr']['En pause'], context['total_hits']) if "En pause" in context['facets']['action_status_fr'] else 360
                context['be_offset'] = circle_progress_bar_offset(context['facets']['action_status_fr']['Behind'], context['total_hits']) if "Behind" in context['facets']['action_status_fr'] else 360
                context['ip_num'] = context['facets']['action_status_fr']['En cours'] if "En cours" in context['facets']['action_status_fr'] else 0
                context['ns_num'] = context['facets']['action_status_fr']['Non entamée'] if "Non entamée" in context['facets']['action_status_fr'] else 0
                context['co_num'] = context['facets']['action_status_fr']['Terminée'] if "Terminée" in context['facets']['action_status_fr'] else 0
                context['bl_num'] = context['facets']['action_status_fr']['En pause'] if "En pause" in context['facets']['action_status_fr'] else 0
                context['be_num'] = context['facets']['action_status_fr']['Behind'] if "Behind" in context['facets']['action_status_fr'] else 0

                for s in ['En cours', 'Non entamée', 'Terminée', 'En pause', 'Behind']:
                    if s in context['facets']['action_status_fr'] and context['facets']['action_status_fr'][s] > 0:
                        context[s.replace(" ", "_").replace('é', 'e') + "_list"] = s
                    else:
                        context[s.replace(" ", "_").replace('é', 'e') + "_list"] = ()

        else:
            if 'action_status' in request.GET:
                statii = request.GET.getlist('action_status')
                stati = statii[0].split('|')
                context['ip_offset'] = circle_progress_bar_offset(context['facets']['action_status']['In Progress'], context['total_hits']) if "In Progress" in stati and 'In Progress' in context['facets']['action_status'] else 360
                context['ns_offset'] = circle_progress_bar_offset(context['facets']['action_status']['Not Started'], context['total_hits']) if "Not Started" in stati and 'Not Started' in context['facets']['action_status'] else 360
                context['co_offset'] = circle_progress_bar_offset(context['facets']['action_status']['Completed'], context['total_hits']) if "Completed" in stati and 'Completed' in context['facets']['action_status'] else 360
                context['bl_offset'] = circle_progress_bar_offset(context['facets']['action_status']['Blocked'], context['total_hits']) if "Blocked" in stati and 'Blocked' in context['facets']['action_status'] else 360
                context['be_offset'] = circle_progress_bar_offset(context['facets']['action_status']['Behind'], context['total_hits']) if "Behind" in stati and 'Behind' in context['facets']['action_status'] else 360

                context['ip_num'] = context['facets']['action_status']['In Progress'] if "In Progress" in stati and 'In Progress' in context['facets']['action_status'] else 0
                context['ns_num'] = context['facets']['action_status']['Not Started'] if "Not Started" in stati and 'Not Started' in context['facets']['action_status'] else 0
                context['co_num'] = context['facets']['action_status']['Completed'] if "Completed" in stati and 'Completed' in context['facets']['action_status'] else 0
                context['bl_num'] = context['facets']['action_status']['Blocked'] if "Blocked" in stati and 'Blocked' in context['facets']['action_status'] else 0
                context['be_num'] = context['facets']['action_status']['Behind'] if "Behind" in stati and 'Behind' in context['facets']['action_status'] else 0

                for s in ['In Progress', 'Not Started', 'Completed', 'Blocked', 'Behind']:
                    stati2 = stati.copy()
                    if s in stati:
                        stati2.remove(s)
                    else:
                        # We do not want to show any links when clicking on the status would result in no change or zero results
                        if s in context['facets']['action_status'] and context['facets']['action_status'][s] > 0:
                            stati2.append(s)
                        elif stati == stati2:
                            stati2 = ()
                    context[s.replace(" ", "_").replace('é', 'e') + "_list"] = "|".join(stati2)

            else:
                context['ip_offset'] = circle_progress_bar_offset(context['facets']['action_status']['In Progress'], context['total_hits']) if "In Progress" in context['facets']['action_status'] else 360
                context['ns_offset'] = circle_progress_bar_offset(context['facets']['action_status']['Not Started'], context['total_hits']) if "Not Started" in context['facets']['action_status'] else 360
                context['co_offset'] = circle_progress_bar_offset(context['facets']['action_status']['Completed'], context['total_hits']) if "Completed" in context['facets']['action_status'] else 360
                context['bl_offset'] = circle_progress_bar_offset(context['facets']['action_status']['Blocked'], context['total_hits']) if "Blocked" in context['facets']['action_status'] else 360
                context['be_offset'] = circle_progress_bar_offset(context['facets']['action_status']['Behind'], context['total_hits']) if "Behind" in context['facets']['action_status'] else 360
                context['ip_num'] = context['facets']['action_status']['In Progress'] if "In Progress" in context['facets']['action_status'] else 0
                context['ns_num'] = context['facets']['action_status']['Not Started'] if "Not Started" in context['facets']['action_status'] else 0
                context['co_num'] = context['facets']['action_status']['Completed'] if "Completed" in context['facets']['action_status'] else 0
                context['bl_num'] = context['facets']['action_status']['Blocked'] if "Blocked" in context['facets']['action_status'] else 0
                context['be_num'] = context['facets']['action_status']['Behind'] if "Behind" in context['facets']['action_status'] else 0

                for s in ['In Progress', 'Not Started', 'Completed', 'Blocked', 'Behind']:
                    if s in context['facets']['action_status'] and context['facets']['action_status'][s] > 0:
                        context[s.replace(" ", "_") + "_list"] = s
                    else:
                        context[s.replace(" ", "_") + "_list"] = ()

    return context, template
