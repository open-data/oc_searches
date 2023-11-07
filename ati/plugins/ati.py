from django.conf import settings
from django.core.cache import caches
from django.http import HttpRequest
import json
import nltk
from nltk.stem import PorterStemmer
import numpy as np
import os
import pickle
from search.models import Search, Field, Code
from SolrClient import SolrResponse
import time


def load_model(path):
    if os.path.exists(path):
        start1 = time.time()
        model = pickle.load(open(path, 'rb'))
        end1 = time.time()
        print('Loading file : {0} sec'.format(end1-start1))
        return model

# Use a local memory cache for the DB objects
cache = caches['local']
# Load Search and Field configuration

stemmer = cache.get('ati_stemmer')
if stemmer is None:
    stemmer = PorterStemmer()
    cache.set('ati_stemmer', stemmer, timeout=3600)

model_en = cache.get('ati_model_en')
if model_en is None:
    classifier_en = os.path.join(settings.NLTK_DATADIR, 'ati_en.model')
    model_en = load_model(classifier_en)
    cache.set('ati_model_en', model_en, timeout=3600)

model_fr = cache.get('ati_model_fr')
if model_fr is None:
    classifier_fr = os.path.join(settings.NLTK_DATADIR, 'ati_fr.model')
    model_fr = load_model(classifier_fr)
    cache.set('ati_model_fr', model_fr, timeout=3600)

if settings.NLTK_DATADIR not in nltk.data.path:
    nltk.data.path.append(settings.NLTK_DATADIR)


def plugin_api_version():
    return 1.1


def pre_search_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_query


def post_search_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    search_terms = np.array([solr_query['q']])

    predicted = {}
    short_list = {}
    if request.LANGUAGE_CODE == 'fr':
        predicted = model_fr.predict_proba(search_terms)[0]
        for index, name in enumerate(model_fr.classes_):
            short_list[index] = {'relevance': predicted[index], 'department': name}
    else:
        predicted = model_en.predict_proba(search_terms)[0]
        for index, name in enumerate(model_en.classes_):
            short_list[index] = {'relevance': predicted[index], 'department': name}

    sorted_list = sorted(short_list, key=lambda x: (short_list[x]['relevance']), reverse=True)

    # Just return the top ten matches
    short_sorted_list = sorted_list[0:10]
    results = []
    for i in short_sorted_list:
        results.append({'relevance': short_list[i]["relevance"], 'department': short_list[i]["department"]})

    extras = {'relevance': results}
    solr_response.data['extras'] = extras

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
    bi_title = f'{solr_record["owner_org_en"]} | {solr_record["owner_org_fr"]}'
    solr_record['owner_org_title'] = bi_title
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
