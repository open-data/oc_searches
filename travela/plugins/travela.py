from django.http import HttpRequest
from django.conf import settings
from search.models import Search, Field, Code
from SolrClient import SolrClient, SolrResponse


def plugin_api_version():
    return 1.0


def pre_search_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_query


def post_search_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_response


def pre_record_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_query


def post_record_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    if len(solr_response.docs) > 0:
        try:
            this_doc = solr_response.docs[0]
            current_year = int(this_doc['year'])
            if request.LANGUAGE_CODE == "fr":
                context['curr_fmt'] = "CAD,fr_CA"
                context['org_title'] = this_doc['owner_org_fr']
            else:
                context['curr_fmt'] = "CAD,en_CA"
                context['org_title'] = this_doc['owner_org_en']

            # If there are ore than 2 years of data, calculate the differences

            previous_year = current_year - 1
            solr_query['q'] = "id:{0},{1}".format(solr_response.docs[0]['owner_org'], previous_year)
            solr = SolrClient(settings.SOLR_SERVER_URL)
            sr = solr.query(search.solr_core_name, solr_query)

            conf_fees = float(this_doc['conference_fees_kdollars'])
            hospitality = float(this_doc['hospitality_kdollars'])

            if len(sr.docs) > 0:
                # Retrieve previous year values and calculate the varience
                prev_doc = sr.docs[0]
                this_doc['variance'] = True
                this_doc['prev_conf_fees'] = float(prev_doc['conference_fees_kdollars'])
                this_doc['var_conf_fees'] = conf_fees - prev_doc['conference_fees_kdollars']
                this_doc['prev_hospitality'] = float(prev_doc['hospitality_kdollars'])
                this_doc['var_hospitality'] = hospitality - prev_doc['hospitality_kdollars']
                this_doc['prev_minister'] = float(prev_doc['minister_kdollars'])
                this_doc['var_minister'] = this_doc['minister_kdollars'] - prev_doc['minister_kdollars']

                if current_year < 2018:
                    ps_dollars = float(this_doc["public_servants_kdollars"])
                    non_ps_dollars = float(this_doc['non_public_servants_kdollars'])

                    this_doc['total_abc'] = ps_dollars + non_ps_dollars + conf_fees + hospitality

                    this_doc['prev_ps_dollars'] = float(prev_doc["public_servants_kdollars"])
                    this_doc['prev_non_ps_dollars'] = float(prev_doc['non_public_servants_kdollars'])
                    this_doc['var_ps_dollars'] = ps_dollars - prev_doc["public_servants_kdollars"]
                    this_doc['var_non_ps_dollars'] = non_ps_dollars - prev_doc['non_public_servants_kdollars']
                    this_doc['total_travel'] = ps_dollars + non_ps_dollars
                    this_doc['prev_total_travel'] = float(prev_doc["public_servants_kdollars"]) + float(prev_doc['non_public_servants_kdollars'])
                    this_doc['var_total_travel'] = this_doc['total_travel'] - this_doc['prev_total_travel']
                    this_doc['prev_total_abc'] = this_doc['prev_ps_dollars'] + this_doc['prev_non_ps_dollars'] + this_doc['prev_conf_fees'] + this_doc['prev_hospitality']
                    this_doc['var_total_abc'] = this_doc['total_abc'] - this_doc['prev_total_abc']
                elif current_year == 2018:
                    this_doc['total_travel'] = float(this_doc['operational_activities_kdollars']) + float(this_doc['key_stakeholders_kdollars']) + float(this_doc['internal_governance_kdollars']) + float(this_doc['training_kdollars']) + float(this_doc['other_kdollars'])
                    this_doc['prev_total_travel'] = float(prev_doc["public_servants_kdollars"]) + float(prev_doc['non_public_servants_kdollars'])
                    this_doc['var_total_travel'] = this_doc['total_travel'] - this_doc['prev_total_travel']
                    this_doc['total_abc'] = this_doc['total_travel'] + conf_fees + hospitality
                    this_doc['prev_total_abc'] = this_doc['prev_total_travel'] + this_doc['prev_conf_fees'] + this_doc['prev_hospitality']
                    this_doc['var_total_abc'] = this_doc['total_abc'] - this_doc['prev_total_abc']
                else:
                    this_doc['prev_op_dollars'] = float(prev_doc['operational_activities_kdollars'])
                    this_doc['prev_key_dollars'] = float(prev_doc['key_stakeholders_kdollars'])
                    this_doc['prev_internal_dollars'] = float(prev_doc['internal_governance_kdollars'])
                    this_doc['prev_training_dollars'] = float(prev_doc['training_kdollars'])
                    this_doc['prev_other_dollars'] = float(prev_doc['other_kdollars'])

                    this_doc['var_op_dollars'] = this_doc['operational_activities_kdollars'] - prev_doc['operational_activities_kdollars']
                    this_doc['var_key_dollars'] = this_doc['key_stakeholders_kdollars'] - prev_doc['key_stakeholders_kdollars']
                    this_doc['var_internal_dollars'] = this_doc['internal_governance_kdollars'] - prev_doc['internal_governance_kdollars']
                    this_doc['var_training_dollars'] = this_doc['training_kdollars'] - prev_doc['training_kdollars']
                    this_doc['var_other_dollars'] = this_doc['other_kdollars'] - prev_doc['other_kdollars']

                    this_doc['total_travel'] = float(this_doc['operational_activities_kdollars']) + float(this_doc['key_stakeholders_kdollars']) + float(this_doc['internal_governance_kdollars']) + float(this_doc['training_kdollars']) + float(this_doc['other_kdollars'])
                    this_doc['prev_total_travel'] = float(this_doc['prev_op_dollars']) + float(this_doc['prev_key_dollars']) + float(this_doc['prev_internal_dollars']) + float(this_doc['prev_training_dollars']) + float(this_doc['prev_other_dollars'])
                    this_doc['var_total_travel'] = this_doc['total_travel'] - this_doc['prev_total_travel']
                    this_doc['total_abc'] = this_doc['total_travel'] + conf_fees + hospitality
                    this_doc['prev_total_abc'] = this_doc['prev_total_travel'] + this_doc['prev_conf_fees'] + this_doc['prev_hospitality']
                    this_doc['var_total_abc'] = this_doc['total_abc'] - this_doc['prev_total_abc']
            else:
                this_doc['variance'] = False
                ps_dollars = float(this_doc["public_servants_kdollars"])
                non_ps_dollars = float(this_doc['non_public_servants_kdollars'])
                if current_year < 2018:
                    this_doc['total_travel'] = ps_dollars + non_ps_dollars
                    this_doc['total_abc'] = ps_dollars + non_ps_dollars + conf_fees + hospitality
                else:
                    this_doc['total_travel'] = float(this_doc['operational_activities_kdollars']) + float(this_doc['key_stakeholders_kdollars']) + float(this_doc['internal_governance_kdollars']) + float(this_doc['training_kdollars']) + float(this_doc['other_kdollars'])
                    this_doc['total_abc'] = this_doc['total_travel'] + conf_fees + hospitality

        except ValueError as ve:
            pass

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
    return True, csv_record


def load_csv_record(csv_record: dict, solr_record: dict, search: Search, fields: dict, codes: dict, format: str):
    # post 2017 Annual Travel records won't have these two columns, so provide placeholders that are needed for the CSV export functionality
    if "non_public_servants_kdollars" not in solr_record or solr_record["non_public_servants_kdollars"] == '':
        solr_record["non_public_servants_kdollars"] = 0
    if "public_servants_kdollars" not in solr_record or solr_record["public_servants_kdollars"] == '':
        solr_record["public_servants_kdollars"] = 0

    # Calculate a total
    total = 0.0
    if int(csv_record['year']) < 2018:
        if csv_record['public_servants_kdollars']:
            total += float(csv_record['public_servants_kdollars'])
        if csv_record['non_public_servants_kdollars']:
            total += float(csv_record['non_public_servants_kdollars'])
    else:
        if csv_record['operational_activities_kdollars']:
            total += float(csv_record['operational_activities_kdollars'])
        if csv_record['key_stakeholders_kdollars']:
            total += float(csv_record['key_stakeholders_kdollars'])
        if csv_record['internal_governance_kdollars']:
            total += float(csv_record['internal_governance_kdollars'])
        if csv_record['training_kdollars']:
            total += float(csv_record['training_kdollars'])
        if csv_record['other_kdollars']:
            total += float(csv_record['other_kdollars'])
    if csv_record['hospitality_kdollars']:
        total += float(csv_record['hospitality_kdollars'])
    if csv_record['conference_fees_kdollars']:
        total += float(csv_record['conference_fees_kdollars'])

    if total >= 100000:
        solr_record['total_range'] = 'r1'
    elif 100000 > total >= 10000:
        solr_record['total_range'] = 'r2'
    elif 10000 > total >= 1000:
        solr_record['total_range'] = 'r3'
    elif 1000 > total >= 100:
        solr_record['total_range'] = 'r4'
    else:
        solr_record['total_range'] = 'r5'

    return solr_record
