from django.conf import settings
from django.http import HttpRequest
from search.models import Search, Field, Code, Setting
from SolrClient import SolrResponse


def plugin_api_version():
    return 1.2


def pre_search_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_query


def post_search_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_response


def pre_record_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_query


def post_record_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_response


def pre_export_solr_query(solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list):
    solr_query['fl'] = str(solr_query['fl']).replace("display_flags,", "")
    solr_query['fl'] = str(solr_query['fl']).replace("creator,", "")
    solr_query['fl'] = str(solr_query['fl']).replace("datastore_enabled_en,", "")
    solr_query['fl'] = str(solr_query['fl']).replace("datastore_enabled_fr,", "")
    solr_query['fl'] = str(solr_query['fl']).replace("imso_approval,", "")
    solr_query['fl'] = str(solr_query['fl']).replace("portal_release_date,", "")
    solr_query['fl'] = str(solr_query['fl']).replace("federated_date_modified,", "")
    solr_query['fl'] = str(solr_query['fl']).replace("date_modified,", "")
    solr_query['fl'] = str(solr_query['fl']).replace("ready_to_publish,", "")
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

def pre_render_search(context: dict, template: str, request: HttpRequest, lang: str, search: Search, fields: dict, codes: dict, view_type='search'):
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

    OPEN_MAPS_MSG_EN = "Search for geospatial data or click **Add to Map List** to select multiple datasets to plot on " \
                       "a single map. Then click **View on Map** to visualize and overlay the datasets using a geospatial viewer "
    OPEN_MAPS_MSG_FR = "Rechercher des données géospatiales ou cliquer sur **Ajouter à la liste de cartes** pour " \
                       "sélectionner de multiples jeux de données à tracer sur une seule carte. " \
                       "Ensuite, cliquez **Afficher la carte** pour visualiser et superposer les jeux de données à " \
                       "l'aide d'une visualisateur géospatiale. "

    MACHINE_XLT_MSG_EN = '<span class="fa fa-language text-muted mrgn-lft-sm" title="This third party metadata ' \
                         'element has been translated using an automated translation tool. To report any ' \
                         'discrepancies please contact PortalSupport-Soutienportail@tbs-sct.gc.ca"></span>'
    MACHINE_XLT_MSG_FR = '<span class="fa fa-language text-muted mrgn-lft-sm" title="Cet élément de métadonnées ' \
                         'provenant d’une tierce partie a été traduit à l’aide d’un outil de traduction automatisée. ' \
                         'Pour signaler toute anomalie, veuillez communiquer avec nous à ' \
                         'PortalSupport-Soutienportail@tbs-sct.gc.ca"></span>'

    context['search_alerts'] = []
    context['od_en_fgp_root'] = settings.OPEN_DATA_EN_FGP_BASE
    context['od_fr_fgp_root'] = settings.OPEN_DATA_FR_FGP_BASE
    context['open_data_url_base'] = settings.OPEN_DATA_BASE_URL_FR if lang == 'fr' else settings.OPEN_DATA_BASE_URL_EN

    # Display a special message if the user has selected "Open Maps" as a filter
    if str(request.GET.get("collection", "")).find("fgp") >= 0:
        if lang == 'fr':
            context['search_alerts'].append(OPEN_MAPS_MSG_FR)
        else:
            context['search_alerts'].append(OPEN_MAPS_MSG_EN)

    # Text to use to indicate machine translation was used.
    if lang == 'fr':
        context["machine_xlt_msg"] = MACHINE_XLT_MSG_FR
    else:
        context['machine_xlt_msg'] = MACHINE_XLT_MSG_EN

    # Determine link for "More like this..."
    if settings.SEARCH_LANG_USE_PATH:
        if lang == 'fr':
            context["mlt_link_path"] = "/rechercher/fr/donneesouvertes/similaire"
        else:
            context["mlt_link_path"] = "/search/en/opendata/similar"
    else:
        if lang == 'fr':
            context["mlt_link_path"] = f'{settings.SEARCH_HOST_PATH}/donneesouvertes/similaire'
        else:
            context["mlt_link_path"] = f'{settings.SEARCH_HOST_PATH}/opendata/similar'

    # Get search drop in message:
    context["custom_search_message_en"] = ""
    search_msg_en, is_new = Setting.objects.get_or_create(key="data.searchpage.topmessage.en")
    if not is_new:
        context["custom_search_message_en"] = search_msg_en.value
    context["custom_search_message_fr"] = ""
    search_msg_fr, is_new = Setting.objects.get_or_create(key="data.searchpage.topmessage.fr")
    if not is_new:
        context["custom_search_message_fr"] = search_msg_fr.value

    if request.META.get("QUERY_STRING", "") == "html":
        template = "more_like_this.html"

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
