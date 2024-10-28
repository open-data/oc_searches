
from babel.dates import format_date
from datetime import datetime
from django.http import HttpRequest
import re
from search.models import Search, Field, Code
from SolrClient import SolrResponse


def plugin_api_version():
    return 1.1


def circle_progress_bar_offset(value: int, total: int):
    if value == 0:
        return 360
    else:
        return 360 - round(value * 360 / total)


def handle_excel_dates(date_value: str):
    return_value = ""

    if re.search(r"^\d{4}-[0-1]\d-[0-3]\d", date_value) is not None:
        # YYYY-MM-DD
        m = re.search(r"^\d{4}-[0-1]\d-[0-3]\d", date_value)
        return_value = m.group(0)

    elif re.search(r"^(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|30|31)/(\d{4}|\d{2})$",date_value) is not None:
        # M/D/Y - with or without leading zeroes
        m = re.search(r"^(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|30|31)/(\d{4}|\d{2})$", date_value)
        year = int(m.group(3)) if len(m.group(3)) == 4 else int(f'20{m.group(3)}')
        day = int(m.group(2))
        month = int(m.group(1))
        return_value = f"{year:04d}-{month:02d}-{day:02d}"
    return return_value


def pre_search_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_query


def post_search_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    solr_query['group'] = True
    solr_query['group.field'] = 'cip_serial'
    solr_query['group.limit'] = 1
    solr_query['group.sort'] = 'reporting_period_no desc'
    solr_query['group.facet'] = True
    solr_query['group.main'] = True
    solr_query['group.truncate'] = True

    solr_query['q'] = f'{solr_query["q"]} AND (is_latest:"T")'

    return context, solr_response


def pre_record_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_id: str):
    id_parts = record_id.split(",")
    if len(id_parts) > 1:
        solr_query['q'] = 'cip_serial:"{0}"'.format(id_parts[0])
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

    csv_record['report'] = csv_record['report'].lower()
    if "/" in csv_record['report']:
        csv_record['report'] = csv_record['report'].split("/")[0]

    if csv_record['status']:
        csv_record['status'] = csv_record['status'].lower().strip().replace(' ', '_')
        csv_record['status_detail'] = csv_record['status']
        if csv_record['status_detail'] == 'implemented':
            csv_record['status_detail'] = 'fully_implemented'
        if csv_record['status'] == 'substantially_implemented':
            csv_record['status'] = "implemented"
        if csv_record['status'] == 'fully_implemented':
            csv_record['status'] = "implemented"

    #  Ensure Code values are used in the report field:
    report_codes_en = {"independent external comprehensive review": "iecr",
                       "third independent review of the national defence act": "ir3",
                       "minister's advisory panel on systemic racism and discrimination final report": "apr",
                       "national apology advisory committee report": "naac",
                       "major policy initiatives": "mpi"}
    if csv_record['report'] in report_codes_en:
        csv_record['report'] = report_codes_en[csv_record['report']]

    if csv_record['completion_date']:
        csv_record['completion_date'] = handle_excel_dates(csv_record['completion_date'])
    if csv_record['actual_date']:
        csv_record['actual_date'] = handle_excel_dates(csv_record['actual_date'])

    return True,  csv_record


def load_csv_record(csv_record: dict, solr_record: dict, search: Search, fields: dict, codes: dict, format: str):

    aspects = {"Defence Team Experience and Wellbeing": "Expérience de l'équipe de la défense et bien-être",
               "Diversity, Equity & Inclusion": "Diversité, équité et inclusion",
               "Professional Conduct": "Conduite professionnelle",
               "Trust in the Institution and Leadership": "Confiance en l'institution et au leadership"}

    if solr_record['culture_aspect']:
        if "/" in solr_record['culture_aspect']:
            aspects = solr_record['culture_aspect'].split("/")
            solr_record['culture_aspect_en'] = aspects[0]
            solr_record['culture_aspect_fr'] = aspects[1]
        elif solr_record['culture_aspect'] in aspects:
            solr_record['culture_aspect_en'] = solr_record['culture_aspect']
            solr_record['culture_aspect_fr'] = aspects[solr_record['culture_aspect']]
        else:
            solr_record['culture_aspect_en'] = "-"
            solr_record['culture_aspect_fr'] = "-"

    if csv_record['completion_date']:
        date_text = csv_record['completion_date']
        completion_date = datetime.strptime(date_text, '%Y-%m-%d')
        solr_record['completion_date'] = date_text
        if completion_date:
            solr_record['completion_date_en'] = f"By {format_date(completion_date, locale='en')}"
            solr_record['completion_date_fr'] = f"D'ici {format_date(completion_date, locale='fr')}"

    if csv_record['actual_date']:
        date_text = csv_record['actual_date']
        completion_date = datetime.strptime(date_text, '%Y-%m-%d')
        solr_record['actual_date'] = date_text
        if completion_date:
            solr_record['actual_date_en'] = f"{format_date(completion_date, locale='en')}"
            solr_record['actual_date_fr'] = f"{format_date(completion_date, locale='fr')}"

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
        context['mi_offset'] = 360
        context['ip_num'] = 0
        context['ns_num'] = 0
        context['co_num'] = 0
        context['mi_num'] = 0
        context['ip_list'] = ()
        context['ns_list'] = ()
        context['co_list'] = ()
        context['mi_list'] = ()
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
            context['ip_offset'] = circle_progress_bar_offset(context['facets']['status']['in_progress'], context['total_hits']) if "in_progress" in stati and 'in_progress' in context['facets']['status'] else 360
            context['ns_offset'] = circle_progress_bar_offset(context['facets']['status']['not_started'], context['total_hits']) if "not_started" in stati and 'not_started' in context['facets']['status'] else 360
            context['co_offset'] = circle_progress_bar_offset(context['facets']['status']['implemented'], context['total_hits']) if "implemented" in stati and 'implemented' in context['facets']['status'] else 360
            context['mi_offset'] = circle_progress_bar_offset(context['facets']['status']['mitigated'], context['total_hits']) if "mitigated" in stati and 'mitigated' in context['facets']['status'] else 360

            context['ip_num'] = context['facets']['status']['in_progress'] if "in_progress" in stati and 'in_progress' in context['facets']['status'] else 0
            context['ns_num'] = context['facets']['status']['not_started'] if "not_started" in stati and 'not_started' in context['facets']['status'] else 0
            context['co_num'] = context['facets']['status']['implemented'] if "implemented" in stati and 'implemented' in context['facets']['status'] else 0
            context['mi_num'] = context['facets']['status']['mitigated'] if "mitigated" in stati and 'mitigated' in context['facets']['status'] else 0

            for s in ['in_progress', 'not_started', 'implemented', 'mitigated']:
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
            context['ip_offset'] = circle_progress_bar_offset(context['facets']['status']['in_progress'], context['total_hits']) if "in_progress" in context['facets']['status'] else 360
            context['ns_offset'] = circle_progress_bar_offset(context['facets']['status']['not_started'], context['total_hits']) if "not_started" in context['facets']['status'] else 360
            context['co_offset'] = circle_progress_bar_offset(context['facets']['status']['implemented'], context['total_hits']) if "implemented" in context['facets']['status'] else 360
            context['mi_offset'] = circle_progress_bar_offset(context['facets']['status']['mitigated'], context['total_hits']) if "mitigated" in context['facets']['status'] else 360
            context['ip_num'] = context['facets']['status']['in_progress'] if "in_progress" in context['facets']['status'] else 0
            context['ns_num'] = context['facets']['status']['not_started'] if "not_started" in context['facets']['status'] else 0
            context['co_num'] = context['facets']['status']['implemented'] if "implemented" in context['facets']['status'] else 0
            context['mi_num'] = context['facets']['status']['mitigated'] if "mitigated" in context['facets']['status'] else 0

            for s in ['in_progress', 'not_started', 'implemented', 'mitigated']:
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
