from babel.dates import format_date
from datetime import datetime
import ckanapi
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone as utimezone
import json
import logging
import pytz
from search.models import Search, Field, Code, Setting, Event
import sys
from SolrClient import SolrClient
from SolrClient.exceptions import ConnectionError as SolrConnectionError

from time import time
import traceback

IGNORED_FIELDS = ['creator_user_id', 'groups', 'isopen', 'license_title', 'license_url', 'notes', 'num_resources',
                  'num_tags', 'private', 'relationships_as_object', 'relationships_as_subject', 'revision_id',
                  'schema', 'state', 'tags', 'title', 'validation_options', 'validation_status',
                  'validation_timestamp', 'version']
BILINGUAL_FIELDS = ['additional_note', 'contributor', 'data_series_issue_identification', 'data_series_name',
                    'maintainer_contact_form',
                    'metadata_contact', 'notes_translated', 'org_section', 'org_title_at_publication',
                    'position_name', 'program_page_url', 'series_publication_dates', 'title_translated']
DATE_FIELDS = {'metadata_created', 'metadata_modified', 'federated_date_modified', 'date_modified'}
# Note: in Solr all resource fieldnames are prefixed with "resource_". resource_type in already prefixed
RESOURCE_FIELDS = ['character_set', 'data_quality', 'datastore_active', 'date_published', 'format', 'language',
                   'name_translated', 'related_relationship', 'related_type', 'resource_type', 'size', 'url']


class Command(BaseCommand):
    help = 'Import CKAN JSON lines of Open Canada packages'

    # class variables that hold the search models
    search_target = None
    solr_core = None
    # search_fields: dict[str, Field] = {}
    search_fields = {}
    all_fields = {}
    all_fields_by_id = {}
    # field_codes: dict[str, Code] = {}
    field_codes = {}
    # Number of rows to commit to Solr at a time
    cycle_on = 1000
    # Logging information
    logger = logging.getLogger(__name__)
    bad_data_list = []
    missing_codes_dict = {}
    error_count = 0
    import_type = 'remote_ckan'

    # creating a mapping between resource fields and Solr fields
    resource_map = {}
    for r in RESOURCE_FIELDS:
        if r.startswith("resource_"):
            resource_map[r] = r
        elif r == "name_translated":
            resource_map["name_translated_en"] = "resource_name_translated_en"
            resource_map["name_translated_fr"] = "resource_name_translated_fr"
        else:
            resource_map[r] = "resource_" + r

    def log_it(self, title, message="", category='info'):
        if category == 'error':
            self.logger.error(title)
        elif category == 'warning':
            self.logger.warning(title)
        else:
            self.logger.info(title)
        event_component = "data_import_ckan_json.remote"
        if self.import_type.lower() == 'jsonl':
            event_component = "data_import_ckan_json.jsonl"
        Event.objects.create(search_id='data', component_id=event_component, title=title, category=category, message=message)
        if category != 'info':
            self.error_count += 1

    def set_value(self, field_name, raw_value, solr_record, id):
        if field_name in IGNORED_FIELDS:
            pass
        elif field_name in BILINGUAL_FIELDS:

            # Note that supported langauge codes include "en" and "fr", and also their automated translation
            # equivalents "en-t-fr" and "fr-t-en". We want to track which fields use automated translation since
            # this is used by the web UI.

            ens = ['en', 'en-t-fr']
            frs = ['fr', 'fr-t-en']
            lang_found = False
            automation = False
            for lang_code in ens:
                if lang_code in raw_value:
                    if isinstance(raw_value[lang_code], str):
                        solr_record[field_name + "_en"] = raw_value[lang_code]
                    else:
                        solr_record[field_name + "_en"] = str(raw_value[lang_code])
                        self.bad_data_list.append(f"Unusual data encountered in record {id} for field {field_name}: {solr_record[field_name + '_en']}")
                    if lang_code == 'en-t-fr':
                        automation = True
                lang_found = True
            if not lang_found:
                solr_record[field_name + "_en"] = "-"
            if automation:
                solr_record['machine_translated_fields'].append(field_name + "_en")

            lang_found = False
            automation = False
            for lang_code in frs:
                if lang_code in raw_value:
                    if isinstance(raw_value[lang_code], str):
                        solr_record[field_name + "_fr"] = raw_value[lang_code]
                    else:
                        solr_record[field_name + "_fr"] = str(raw_value[lang_code])
                        self.bad_data_list.append(f"Unusual data encountered in record {id} for field {field_name}: {solr_record[field_name + '_fr']}")
                    if lang_code == 'fr-t-en':
                        automation = True
                lang_found = True
            if not lang_found:
                solr_record[field_name + "_fr"] = "-"
            if automation:
                solr_record['machine_translated_fields'].append(field_name + "_fr")

        elif field_name in DATE_FIELDS:
            # Requires Python 3.9+ This line cna replace the clunky IF statement
            # raw_date = datetime.fromisoformat(raw_value)
            try:
                if 'T' in raw_value:
                    raw_date = datetime.strptime(raw_value, "%Y-%m-%dT%H:%M:%S.%f")
                elif len(raw_value) == 10:
                    raw_date = datetime.strptime(raw_value, "%Y-%m-%d")
                elif len(raw_value) == 20:
                    raw_date = datetime.strptime(raw_value, "%Y-%m-%d %H:%M:%S")
                else:
                    raw_date = datetime.strptime(raw_value[0:10], "%Y-%m-%d")
            except ValueError as ve:
                raw_date = datetime.strptime("1970-01-01", "%Y-%m-%d")
                self.log_it(title=f"Cannot parse ISO date value {raw_value} for field {field_name} in dataset {id}", category='warning')

            solr_record[field_name] = raw_value
            solr_record[field_name + '_en'] = format_date(raw_date, locale='en')
            solr_record[field_name + '_fr'] = format_date(raw_date, locale='fr')
        elif field_name in self.search_fields:
            # Empty values are problematic since Solr won't index a blank space. Use the dash as the understood
            # indicator for an empty value
            if raw_value is None or not raw_value:
                raw_value = "-"
            if self.search_fields[field_name].solr_field_is_coded:
                # self.logger.info(f'Field: {field_name}, Value: {raw_value}')
                if type(raw_value) == list:
                    values = []
                    values_en = []
                    values_fr = []
                    for val in raw_value:
                        values.append(val)
                        if val in self.field_codes[field_name]:
                            values_en.append(self.field_codes[field_name][val].label_en)
                            values_fr.append(self.field_codes[field_name][val].label_fr)
                        elif val != "-" and val not in self.missing_codes_dict:
                            self.missing_codes_dict[val] = f"Unknown code {val} for field {field_name} in dataset {id}"
                    if len(values) > 0:
                        solr_record[field_name] = ",".join(values)
                        solr_record[field_name + "_en"] = ",".join(values_en)
                        solr_record[field_name + "_fr"] = ",".join(values_fr)
                    else:
                        solr_record[field_name] = ["-"]
                        solr_record[field_name + "_en"] = ["-"]
                        solr_record[field_name + "_fr"] = ["-"]
                else:
                    ri = str(raw_value).lower()
                    solr_record[field_name] = raw_value
                    if ri in self.field_codes[field_name]:
                        solr_record[field_name + "_en"] = self.field_codes[field_name][ri].label_en
                        solr_record[field_name + "_fr"] = self.field_codes[field_name][ri].label_fr
                    elif ri != '-':
                        if ri not in self.missing_codes_dict:
                            self.missing_codes_dict[ri] = f"Unknown code {ri} for field {field_name} in dataset {id}"
                        solr_record[field_name + "_en"] = "-"
                        solr_record[field_name + "_fr"] = "-"
            else:
                solr_record[field_name] = raw_value

        return solr_record

    def handle_resources(self, resources, solr_record, ds_id):

        # create dict of lists to hold the collected multi-value resource fields
        solr_resources = {}
        datastore_enabled = False
        for r in self.resource_map:
            solr_resources[self.resource_map[r]] = []
        solr_resources['resource_character_set_en'] = []
        solr_resources['resource_character_set_fr'] = []
        solr_resources['resource_language_en'] = []
        solr_resources['resource_language_fr'] = []
        solr_resources['resource_format_en'] = []
        solr_resources['resource_format_fr'] = []
        solr_resources['resource_related_type_en'] = []
        solr_resources['resource_related_type_fr'] = []
        solr_resources['resource_related_relationship_en'] = []
        solr_resources['resource_related_relationship_fr'] = []
        solr_resources['resource_type_en'] = []
        solr_resources['resource_type_fr'] = []
        solr_resources['resource_data_quality_en'] = []
        solr_resources['resource_data_quality_fr'] = []

        # set a list of unique file formats for the dataset as a whole
        formats = []
        formats_en = []
        formats_fr = []

        for res in resources:
            for res_value in RESOURCE_FIELDS:
                if res_value in res:
                    if res_value == "name_translated":
                        if 'en' in res[res_value]:
                            solr_resources[self.resource_map[res_value + "_en"]].append(res[res_value]['en'])
                        elif 'en-t-fr' in res[res_value]:
                            solr_resources[self.resource_map[res_value + "_en"]].append(res[res_value]['en-t-fr'])
                        if 'fr' in res[res_value]:
                            solr_resources[self.resource_map[res_value + "_fr"]].append(res[res_value]['fr'])
                        elif 'fr-t-en' in res[res_value]:
                            solr_resources[self.resource_map[res_value + "_fr"]].append(res[res_value]['fr-t-en'])
                    elif res_value == "datastore_active":
                        if res[res_value]:
                            datastore_enabled = True
                    elif isinstance(res[res_value], list):
                        if len(res[res_value]) > 0:
                            solr_resources[self.resource_map[res_value]].append(",".join(res[res_value]))
                        else:
                            solr_resources[self.resource_map[res_value]].append('-')
                        if res_value == 'language':
                            if res[res_value]:
                                for l in res[res_value]:
                                    if l.lower() in self.field_codes['resource_language']:
                                        solr_resources['resource_language_en'].append(
                                            self.field_codes['resource_language'][l.lower()].label_en)
                                        solr_resources['resource_language_fr'].append(
                                            self.field_codes['resource_language'][l.lower()].label_fr)
                                    else:
                                        self.log_it(f"Unknown code {l} for resource_language in dataset {id}")
                            else:
                                solr_resources['resource_language_en'].append('-')
                                solr_resources['resource_language_fr'].append('-')

                        elif res_value == 'data_quality':
                            if res[res_value] and len(res[res_value]) > 0:
                                for dq in res[res_value]:
                                    if dq.lower() in self.field_codes['resource_data_quality']:
                                        solr_resources['resource_data_quality_en'].append(
                                            self.field_codes['resource_data_quality'][dq.lower()].label_en)
                                        solr_resources['resource_data_quality_fr'].append(
                                            self.field_codes['resource_data_quality'][dq.lower()].label_fr)
                                    else:
                                        self.log_it(f"Unknown code {dq} for resource_data_quality in dataset {id}")
                            else:
                                solr_resources['resource_data_quality_en'].append('-')
                                solr_resources['resource_data_quality_fr'].append('-')
                            solr_resources['resource_data_quality'].append(res[res_value] if res[res_value] else "-")

                    elif res_value == 'character_set':
                        # Coded value needs two fields
                        if res[res_value]:
                            if res[res_value].lower() in self.field_codes['resource_character_set']:
                                solr_resources['resource_character_set_en'].append(self.field_codes['resource_character_set'][res[res_value].lower()].label_en)
                                solr_resources['resource_character_set_fr'].append(self.field_codes['resource_character_set'][res[res_value].lower()].label_fr)
                            else:
                                self.log_it(title=f"Unknown resource character set code: {res[res_value]} in dataset {ds_id}", category='error')
                        else:
                            solr_resources['resource_character_set_en'].append('-')
                            solr_resources['resource_character_set_fr'].append('-')
                        solr_resources['resource_character_set'].append(res[res_value] if res[res_value] else "-")
                    elif res_value == 'format':
                        if res[res_value]:
                            if res[res_value].lower() in self.field_codes['resource_format']:
                                solr_resources['resource_format_en'].append(self.field_codes['resource_format'][res[res_value].lower()].label_en)
                                solr_resources['resource_format_fr'].append(self.field_codes['resource_format'][res[res_value].lower()].label_fr)
                            else:
                                self.log_it(title=f"Unknown resource format code: {res[res_value]} in dataset {ds_id}", category='error')
                        else:
                            solr_resources['resource_format_en'].append('-')
                            solr_resources['resource_format_fr'].append('-')
                        solr_resources['resource_format'].append(res[res_value] if res[res_value] else "-")
                    elif res_value == 'related_type':
                        if res[res_value]:
                            if res[res_value].lower() in self.field_codes['resource_related_type']:
                                solr_resources['resource_related_type_en'].append(self.field_codes['resource_related_type'][res[res_value].lower()].label_en)
                                solr_resources['resource_related_type_fr'].append(self.field_codes['resource_related_type'][res[res_value].lower()].label_fr)
                            else:
                                self.log_it(title=f"Unknown resource type code: {res[res_value]} in dataset {ds_id}", category='error')
                        else:
                            solr_resources['resource_related_type_en'].append('-')
                            solr_resources['resource_related_type_fr'].append('-')
                        solr_resources['resource_related_type'].append(res[res_value] if res[res_value] else "-")
                    elif res_value == 'related_relationship':
                        if res[res_value]:
                            if res[res_value].lower() in self.field_codes['resource_related_relationship']:
                                solr_resources['resource_related_relationship_en'].append(self.field_codes['resource_related_relationship'][res[res_value].lower()].label_en)
                                solr_resources['resource_related_relationship_fr'].append(self.field_codes['resource_related_relationship'][res[res_value].lower()].label_fr)
                            else:
                                self.log_it(title=f"Unknown resource relationship code: {res[res_value]} in dataset {ds_id}", category='error')
                        else:
                            solr_resources['resource_related_relationship_en'].append('-')
                            solr_resources['resource_related_relationship_fr'].append('-')
                        solr_resources['resource_related_relationship'].append(res[res_value] if res[res_value] else "-")
                    elif res_value == 'resource_type':
                        if res[res_value]:
                            if res[res_value].lower() in self.field_codes['resource_type']:
                                solr_resources['resource_type_en'].append(self.field_codes['resource_type'][res[res_value].lower()].label_en)
                                solr_resources['resource_type_fr'].append(self.field_codes['resource_type'][res[res_value].lower()].label_fr)
                            else:
                                self.log_it(f"Unknown resource type code {res[res_value]} in dataset {ds_id}", category='error')
                        else:
                            solr_resources['resource_type_en'].append('-')
                            solr_resources['resource_type_fr'].append('-')
                        solr_resources['resource_type'].append(res[res_value] if res[res_value] else "-")
                    else:
                        solr_resources[self.resource_map[res_value]].append(res[res_value])
                    if res_value == "format":
                        if not res["format"] in formats and res['format']:
                            formats.append(res["format"])
                            if res["format"].lower() in self.field_codes['resource_format']:
                                formats_en.append(self.field_codes['resource_format'][res['format'].lower()].label_en)
                                formats_fr.append(self.field_codes['resource_format'][res['format'].lower()].label_fr)
                            else:
                                self.log_it(f"Unknown resource format code: {res['format']} in dataset {ds_id}", category='error')
                else:
                    if res_value in self.resource_map:
                        solr_resources[self.resource_map[res_value]].append('-')
                    # Open Maps doesn't set the character_set field
                    if res_value == 'character_set':
                        solr_resources['resource_character_set_en'].append('-')
                        solr_resources['resource_character_set_fr'].append('-')
                    elif res_value == 'language':
                        solr_resources['resource_language_en'].append('-')
                        solr_resources['resource_language_fr'].append('-')
                    elif res_value == 'data_quality':
                        solr_resources['resource_data_quality_en'].append('-')
                        solr_resources['resource_data_quality_fr'].append('-')
                    elif res_value == 'format':
                        solr_resources['resource_format_en'].append('-')
                        solr_resources['resource_format_fr'].append('-')
                    elif res_value == 'related_type':
                        solr_resources['resource_related_type_en'].append('-')
                        solr_resources['resource_related_type_fr'].append('-')
                    elif res_value == 'related_relationship':
                        solr_resources['resource_related_relationship_en'].append('-')
                        solr_resources['resource_related_relationship_fr'].append('-')

        solr_record['formats'] = formats
        solr_record['formats_en'] = formats_en
        solr_record['formats_fr'] = formats_fr

        if datastore_enabled:
            solr_record['datastore_enabled'] = 'True'
        else:
            solr_record['datastore_enabled'] = 'False'
        solr_record.update(solr_resources)
        return solr_record
        # format, language[], name_translated, resource_type, url

    def add_arguments(self, parser):
        parser.add_argument('--search', type=str, help='The Search ID that is being loaded', required=True)
        parser.add_argument('--type', choices=['jsonl', 'remote_ckan'], required=True,
                            help="Select method to load CKAN data. Valid choices are 'jsonl', 'local_ckan', 'remote_ckan'")
        parser.add_argument('--jsonl', type=str,
                            help='JSON lines filename to import when importing a CKAN dataset dump', required=False)
        parser.add_argument('--remote_ckan', type=str, help="The remote CKAN URL when using Remote CKAN")
        parser.add_argument('--reset', action="store_true", help="Delete all existing Solr records before loading")
        parser.add_argument('--quiet', required=False, action='store_true', default=False,
                            help='Only display error messages')

    def set_empty_fields(self, solr_record: dict):

        for sf in self.all_fields:
            if sf not in ['default_fmt', 'unique_identifier', ]:
                self.set_empty_field(solr_record, sf)
        return solr_record

    def set_empty_field(self, solr_record: dict, sf: Field):
        if (sf.field_id not in solr_record) \
            or solr_record[sf.field_id] == '' \
            or ((isinstance(solr_record[sf.field_id], list) and len(solr_record[sf.field_id]) < 1)) \
            or ((isinstance(solr_record[sf.field_id], list) and solr_record[sf.field_id][0] == '')):
            if sf.default_export_value:
                default_fmt = sf.default_export_value.split('|')
                if default_fmt[0] in ['str', 'date']:
                    solr_record[sf.field_id] = str(default_fmt[1])
                    if sf.solr_field_is_coded:
                        solr_record[sf.field_id + "_en"] = str(default_fmt[1])
                        solr_record[sf.field_id + "_fr"] = str(default_fmt[1])
                elif default_fmt[0] == 'int':
                    solr_record[sf.field_id] = int(default_fmt[1])
                    if sf.solr_field_is_coded:
                        solr_record[sf.field_id + "_en"] = int(default_fmt[1])
                        solr_record[sf.field_id + "_fr"] = int(default_fmt[1])
                elif default_fmt[0] == 'float':
                    solr_record[sf.field_id] = float(default_fmt[1])
                    if sf.solr_field_is_coded:
                        solr_record[sf.field_id + "_en"] = float(default_fmt[1])
                        solr_record[sf.field_id + "_fr"] = float(default_fmt[1])
                else:
                    solr_record[sf.field_id] = '-'
            else:
                solr_record[sf.field_id] = '-'
        elif solr_record[sf.field_id] == "":
            solr_record[sf.field_id] = '-'

    def jsons_to_dataset(self, ds):
        """ Convert a CKAN JSON object to the OCSS Data search JSON object """

        solr_record = {'machine_translated_fields': ['-'],
                       'subject': [],
                       'subject_en': [],
                       'subject_fr': [],
                       'spatial_representation_type': [],
                       'spatial_representation_type_en': [],
                       'spatial_representation_type_fr': []}

        for f in ds:
            # Organization, resources, and type requires special handling
            if f == 'organization':
                org = ds[f]['name']
                solr_record = self.set_value('owner_org', org, solr_record, ds['id'])
            elif f == 'owner_org':
                # Ignore the root owner_org - it is a CKAN UUID
                pass
            elif f == 'resources':
                solr_record = self.handle_resources(ds[f], solr_record, ds_id=ds['id'])
            elif f == 'type':
                solr_record = self.set_value('dataset_type', ds[f], solr_record, ds['id'])
            elif f == "spatial_representation_type":
                for srt in ds[f]:
                    if srt in self.field_codes['spatial_representation_type']:
                        solr_record['spatial_representation_type_en'].append(self.field_codes['spatial_representation_type'][srt].label_en)
                        solr_record['spatial_representation_type_fr'].append(self.field_codes['spatial_representation_type'][srt].label_fr)
                        solr_record['spatial_representation_type'].append(srt)
                    else:
                        self.log_it(f"Unknown spatial representation type {srt} in dataset {ds['id']}")
                if len(solr_record['spatial_representation_type']) == 0:
                    solr_record['spatial_representation_type_en'] = ['-']
                    solr_record['spatial_representation_type_fr'] = ['-']
                    solr_record['spatial_representation_type'] = ['-']
            elif f == "subject":
                for s in ds[f]:
                    if s in self.field_codes['subject']:
                        solr_record['subject_en'].append(self.field_codes['subject'][s].label_en)
                        solr_record['subject_fr'].append(self.field_codes['subject'][s].label_fr)
                        solr_record['subject'].append(s)
                    else:
                        self.log_it(f"Unknown subject {s} in dataset {ds['id']}")
            elif f == "title_translated":
                if 'en' in ds[f]:
                    solr_record['title_translated_eng'] = ds[f]['en'].strip()
                    solr_record['title_translated_en'] = ds[f]['en'].strip()
                if 'en-t-fr' in ds[f]:
                    solr_record['title_translated_eng'] = ds[f]['en-t-fr'].strip()
                    solr_record['title_translated_en'] = ds[f]['en-t-fr'].strip()
                if 'fr' in ds[f]:
                    solr_record['title_translated_fra'] = ds[f]['fr'].strip()
                    solr_record['title_translated_fr'] = ds[f]['fr'].strip()
                if 'fr-t-en' in ds[f]:
                    solr_record['title_translated_fra'] = ds[f]['fr-t-en'].strip()
                    solr_record['title_translated_fr'] = ds[f]['fr-t-en'].strip()

            elif f == 'keywords':
                if 'en' in ds[f]:
                    solr_record['keywords_en'] = ds[f]['en']
                    solr_record['keywords_en_text'] = ds[f]['en']
                if 'en-t-fr' in ds[f]:
                    solr_record['keywords_en'] = ds[f]['en-t-fr']
                    solr_record['keywords_en_text'] = ds[f]['en-t-fr']
                    solr_record['machine_translated_fields'].append('keywords_en')
                if 'fr' in ds[f]:
                    solr_record['keywords_fr'] = ds[f]['fr']
                    solr_record['keywords_fr_text'] = ds[f]['fr']
                if 'fr-t-en' in ds[f]:
                    solr_record['keywords_fr'] = ds[f]['fr-t-en']
                    solr_record['keywords_fr_text'] = ds[f]['fr-t-en']
                    solr_record['machine_translated_fields'].append('keywords_fr')
            elif f == "credit":
                if isinstance(ds[f], list):
                    c_en = []
                    c_fr = []
                    for c in ds[f]:
                        if 'credit_name' in c:
                            if 'en' in c['credit_name']:
                                c_en.append(c['credit_name']['en'])
                            if 'fr' in c['credit_name']:
                                c_fr.append(c['credit_name']['fr'])
                    if len(c_en) > 0:
                        solr_record['credit_en'] = c_en
                    else:
                        solr_record['credit_en'] = ['-']
                    if len(c_fr) > 0:
                        solr_record['credit_fr'] = c_fr
                    else:
                        solr_record['credit_fr'] = ['-']
                else:
                    pass
            else:
                solr_record = self.set_value(f, ds[f], solr_record, ds['id'])

        # Ensure all empty CSV fields are set to appropriate or default values
        solr_record = self.set_empty_fields(solr_record)
        solr_record['machine_translated_fields'] = ",".join(solr_record['machine_translated_fields'])

        return solr_record

    def handle(self, *args, **options):

        solr_records = []
        total = 0
        original_checkpoint_ts = utimezone.now()
        self.import_type = options['type']

        try:
            # Retrieve the Search  and Field models from the database
            solr = SolrClient(settings.SOLR_SERVER_URL)

            self.search_target = Search.objects.get(search_id=options['search'])
            self.solr_core = self.search_target.solr_core_name
            self.all_fields = Field.objects.filter(search_id=self.search_target).order_by('field_id')

            for f in self.all_fields:
                self.all_fields_by_id[f.field_id] = f;
            if options['quiet']:
                self.logger.level = logging.WARNING
            sf = Field.objects.filter(search_id=self.search_target,
                                      alt_format='ALL') | Field.objects.filter(
                search_id=self.search_target, alt_format='')
            if options['reset']:
                solr.delete_doc_by_query(self.solr_core, "*:*")
                self.logger.info("Purging all records")

            for search_field in sf:
                self.search_fields[search_field.field_id] = search_field
                codes = Code.objects.filter(field_fid=search_field)
                # Most csv_fields will not  have codes, so the queryset will be zero length
                if len(codes) > 0:
                    code_dict = {}
                    for code in codes:
                        code_dict[code.code_id.lower()] = code
                    self.field_codes[search_field.field_id] = code_dict

            if options['type'] == 'jsonl':
                with open(options['jsonl'], 'r', encoding='utf-8-sig', errors="ignore") as json_file:
                    for dataset in json_file:
                        ds = json.loads(dataset)
                        solr_record = self.jsons_to_dataset(ds)
                        solr_records.append(solr_record)
                        # self.logger.info(json.dumps(solr_record, indent=4))

                        # Write to Solr whenever the cycle threshold is reached
                        if len(solr_records) >= self.cycle_on:
                            # try to connect to Solr up to 10 times
                            for countdown in reversed(range(10)):
                                try:
                                    solr.index(self.solr_core, solr_records)
                                    cycle = 0
                                    if not options['quiet']:
                                        self.logger.info(f'Sent {len(solr_records)} to Solr')
                                    total += len(solr_records)
                                    solr_records.clear()
                                    break
                                except SolrConnectionError as cex:
                                    if not countdown:
                                        raise
                                    self.logger.error(
                                        "Solr error: {0}. Waiting to try again ... {1}".format(cex, countdown))
                                    time.sleep((10 - countdown) * 5)

            elif options['type'] == 'remote_ckan':
                object_ids = {}
                with ckanapi.RemoteCKAN(options['remote_ckan'], 'oc_search/2.0 (+http://open.camada.ca/search)') as remote_ckan:

                    # Determine the last activity that was indexed by retrieving these settings from the database
                    ckan_checkpoint_id, created_id = Setting.objects.get_or_create(key="data.checkpoint.dataset_id")
                    ckan_checkpoint_ts, created_ts = Setting.objects.get_or_create(key="data.checkpoint.dataset_timestamp")
                    original_checkpoint_ts = ckan_checkpoint_ts
                    offset = 0

                    # Assume Open Canada activities are using UTC time
                    activity_ts = pytz.utc.localize(datetime.utcnow())
                    if not created_ts:
                        last_ts = pytz.utc.localize(datetime.fromisoformat(ckan_checkpoint_ts.value))
                    else:
                        last_ts = pytz.utc.localize(activity_ts)
                    checkpoint_ts = last_ts

                    # Keep calling the CKAN Recently_changed_packages_activity_list API until we see an activity
                    # with the same or older timestamp that was saved to the database.
                    while activity_ts > last_ts:
                        response_json = remote_ckan.action.recently_changed_packages_activity_list(offset=offset, limit=50)
                        for activity in response_json:
                            self.logger.info(f"{activity['object_id']}: {activity['timestamp']}")
                            activity_ts = pytz.utc.localize(datetime.fromisoformat(activity["timestamp"]))

                            # stop processing if we have reached the previously save checkpoint
                            # NOTE - assumption was made here that the activity timestamp alone was sufficient to
                            #        use as a checkpoint, and the dataset ID is not compared either.
                            if activity_ts <= last_ts:
                                break

                            # Because CKAN returns activities from newest to oldest, we do not want to process
                            # older activities for the same dataset that have already been overriden by a newer
                            # activity
                            if activity['object_id'] in object_ids:
                                if activity_ts < object_ids[activity['object_id']]:
                                    continue
                            object_ids[activity['object_id']] = activity_ts

                            # Update the Solr record for additions and updates, remove from solr for deleted packages
                            if activity['activity_type'] in ["changed package", "new package"]:
                                solr_record = self.jsons_to_dataset(activity['data']['package'])
                                solr_records.append(solr_record)
                            elif activity['activity_type'] == "deleted package":
                                solr.delete_doc_by_query(self.solr_core, f"id:{activity['object_id']}")

                            # Update the checkpoint value, but do not save to the database until the end of the
                            # processing run
                            if activity_ts > checkpoint_ts:
                                ckan_checkpoint_id.value = activity['object_id']
                                ckan_checkpoint_ts.value = activity_ts.strftime("%Y-%m-%dT%H:%M:%S.%f")
                                checkpoint_ts = activity_ts
                        offset += 50

                    # Save the activity checkpoint to the database
                    ckan_checkpoint_id.save()
                    ckan_checkpoint_ts.save()

            else:
                raise Exception("Unknown type")

            # Do a final index and commit the changes
            for countdown in reversed(range(10)):
                try:
                    if len(solr_records) > 0:
                        solr.index(self.solr_core, solr_records)
                        self.logger.info(f'Sent {len(solr_records)} to Solr')
                        total += len(solr_records)
                    solr_records.clear()
                    solr.commit(self.solr_core, softCommit=True, waitSearcher=True)
                    break
                except SolrConnectionError as cex:
                    if not countdown:
                        raise
                    self.logger.error(
                        "Solr error: {0}. Waiting to try again ... {1}".format(cex, countdown))
                    time.sleep((10 - countdown) * 5)

            solr.commit(self.solr_core)

            # Log the badly formatted data
            if len(self.bad_data_list) > 0 and not options['quiet']:
                self.log_it(title="Poorly formatted data found in records", message="\r".join(self.bad_data_list), category='warning')
            for err_msg in self.missing_codes_dict:
                self.log_it(title=f"Error: {err_msg}", category='warning')

            # log final results
            event_msg = ""
            if options['type'] == 'jsonl':
                event_msg = f"Command imported {total} records from {options['jsonl']}\rOptions:\r  Type - Jsonl,\r  Reset - {options['reset']},\r  Quiet - {options['quiet']}"
            elif options['type'] == 'remote_ckan':
                event_msg = f"Command read {total} datasets from {options['remote_ckan']} starting from {original_checkpoint_ts}\rOptions:\r  Type - Remote_CKAN,\r  Reset - {options['reset']},\r  Quiet - {options['quiet']}"
            event_category = 'success'
            if self.error_count > 0:
                event_category = 'warning'
                event_msg = event_msg + f"\r{self.error_count} Data errors encountered, and {len(self.bad_data_list)} records contain data issues"
            self.log_it(title=f"Loaded {total} datasets", category=event_category, message=event_msg)

        except Search.DoesNotExist as x:
            event_msg = f'Provided search id not found: {options["search"]}'
            self.logger.error(event_msg)
            Event.objects.create(search_id='data', component_id='data_import_ckan_json', title=event_msg, category='warning')
            exit(-1)
        except Field.DoesNotExist as x1:
            event_msg = f"Field {x1} not found in search {options['search']}"
            self.logger.error(event_msg)
            Event.objects.create(search_id='data', component_id='data_import_ckan_json', title=event_msg, category='error')
        except (ckanapi.CKANAPIError, ckanapi.ServerIncompatibleError) as cke:
            event_msg = f"Error while attempting to connect to CKAN at {options['remote_ckan']}: {cke}"
            self.logger.error(event_msg)
            Event.objects.create(search_id='data', component_id='data_import_ckan_json', title=event_msg, category='error')
        except ConnectionError as cr:
            event_msg = f"Connection Refused Error while attempting to connect to CKAN at {options['remote_ckan']}: {cr}"
            self.logger.error(event_msg)
            Event.objects.create(search_id='data', component_id='data_import_ckan_json', title=event_msg, category='error')
        except Exception as x:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            event_msg = f"Command had unexpected exception. \nOptions: {options}. \nTraceback: {traceback.format_exception(exc_type, exc_value,exc_traceback)}"
            self.logger.error(event_msg)
            Event.objects.create(search_id='data', component_id='data_import_ckan_json', title="Unhandled exception", message=event_msg, category='error')
