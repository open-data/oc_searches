from babel.dates import format_date
from babel.numbers import format_decimal
import csv
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from django.conf import settings
import json
import logging
from search.models import Search, Field, Code
from SolrClient import SolrClient
from SolrClient.exceptions import ConnectionError
import time
import traceback


class Command(BaseCommand):
    help = 'Import Suggested Datasets data from Drupal and CKAN'

    logger = logging.getLogger(__name__)
    # class variables that hold the search models
    search_target = None
    solr_core = None
    # search_fields: dict[str, Field] = {}
    search_fields = {}
    all_fields = {}
    # field_codes: dict[str, Code] = {}
    field_codes = {}

    # a working lost of the status updates for a given CKAN S.D. record
    ckan_ds_status = {}

    def add_arguments(self, parser):
        parser.add_argument('--search', type=str, help='The Search ID that is being loaded', required=True)
        parser.add_argument('--drupal_csv', type=str, help='The Drupal Suggested Datasets CSV export file', required=True)
        parser.add_argument('--ckan_json', type=str, help='The CKAN props dataset export file', required=True)
        parser.add_argument('--logging', choices=['debug', 'info', 'warning', 'error', 'critical'], required=False, default='info',
                            help="Select python logging level")
        parser.add_argument('--no_reset', required=False, action='store_true', default=False,
                            help="Purge the Solr core and reload the data")

    def handle(self, *args, **options):

        solr_records = []
        try:
            # Retrieve the Search, Field, and Code models from the Django database
            solr = SolrClient(settings.SOLR_SERVER_URL)
            try:
                self.search_target = Search.objects.get(search_id=options['search'])
                self.solr_core = self.search_target.solr_core_name
                self.all_fields = Field.objects.filter(search_id=self.search_target).order_by('field_id')
                self.all_fields_dict = {}

                for f in self.all_fields:
                    self.all_fields_dict[f.field_id] = f
                if options['logging']:
                    log_level_map = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARNING, 'error': logging.ERROR, 'critical': logging.CRITICAL}
                    self.logger.level = log_level_map[options['logging']]
                sf = Field.objects.filter(search_id=self.search_target,
                                          alt_format='ALL') | Field.objects.filter(
                    search_id=self.search_target, alt_format='')
                if not options['no_reset']:
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

            except Search.DoesNotExist as x:
                self.logger.error('Search not found: "{0}"'.format(x))
                exit(-1)
            except Field.DoesNotExist as x1:
                self.logger.error('Fields not found for search: "{0}"'.format(x1))

            # Load the latest dataset status codes from CKAN. These are loaded from a JSON file generated with the ckanapi utility
            # "ckanapi search datasets include_private=true q=type:prop"

            with open(options['ckan_json'], 'r', encoding='utf-8', errors="ignore") as ckan_file:
                records = ckan_file.readlines()
                for record in records:
                    ds = json.loads(record)

                    # Assumption made here that the mandatory 'id',and 'date_forwarded' fields are present. If there are
                    # no status entries then the S.D. has been sent to the department but no one from the department
                    # has logged onto the registry and updated the dataset set. In that case, use department_contacted as the one and only update.
                    if 'id' in ds and 'date_forwarded' in ds:
                        if 'status' in ds:
                            self.ckan_ds_status[ds['id']] = {'status': ds['status'], 'date_forwarded': ds['date_forwarded']}
                        else:
                            self.ckan_ds_status[ds['id']] = {'status': [{'date': ds['date_forwarded'],
                                                                         'reason': 'department_contacted'}],
                                                                         'date_forwarded': ds['date_forwarded']}


            # Load the Drupal CSV file
            i = 0
            solr_items = []
            with open(options['drupal_csv'], 'r', encoding='utf-8-sig', errors="ignore") as sd_file:
                sd_reader = csv.DictReader(sd_file, dialect='excel')
                for sd in sd_reader:

                    # Check that there is a matching CKAN record for the Drupal record
                    if sd['uuid'] not in self.ckan_ds_status:
                        self.logger.warning(f"No CKAN suggested dataset found for Drupal suggested dataset {sd['uuid']}")
                        continue

                    # Set some dates for the suggested dataset. Set a default date of 2000-01-01 to indicate missing dates
                    date_created = datetime(2000, 1, 1, 0, 0, 0, 0, timezone.utc)
                    try:
                        date_created = datetime.strptime(sd['date_created'], '%Y-%m-%d')
                    except (ValueError, TypeError):
                        self.logger.warning(f"Bad created date time string '{sd['date_created']} for suggestion ID {sd['suggestion_id']}")

                    date_forwarded = datetime(2000, 1, 1, 0, 0, 0, 0, timezone.utc)
                    try:
                        if sd['uuid'] in self.ckan_ds_status:
                            date_forwarded = datetime.strptime(self.ckan_ds_status[sd['uuid']]['date_forwarded'], '%Y-%m-%d')
                    except (ValueError, TypeError):
                        self.logger.warning(f"Bad forwarded date time string '{sd['date_forwarded']} for suggestion UUID {sd['uuid']}")

                    date_released = datetime(2000, 1, 1)
                    try:
                        if sd['uuid'] in self.ckan_ds_status and sd['dataset_released_date']:
                            date_released = datetime.strptime(sd['dataset_released_date'], '%Y-%m-%d')
                    except (ValueError, TypeError):
                        self.logger.warning(f"Bad release date time string '{sd['dataset_released_date']} for suggestion UUID {sd['uuid']}")

                    # Create The Solr record from the Drupal record
                    solr_rec = {
                        'id': sd['uuid'],
                        'title_en': sd['title_en'],
                        'title_eng': sd['title_en'],
                        'title_fr': sd['title_fr'],
                        'title_fra': sd['title_fr'],
                        'owner_org': sd['organization'],
                        'owner_org_en': self.field_codes['owner_org'][sd['organization']].label_en,
                        'owner_org_eng': self.field_codes['owner_org'][sd['organization']].label_en,
                        'owner_org_fr': self.field_codes['owner_org'][sd['organization']].label_fr,
                        'owner_org_fra': self.field_codes['owner_org'][sd['organization']].label_fr,
                        'desc_en': sd['description_en'],
                        'desc_eng': sd['description_en'],
                        'desc_fr': sd['description_fr'],
                        'desc_fra': sd['description_fr'],
                        'linked_ds': sd['dataset_suggestion_status_link'],
                        'votes': sd['votes'],
                        'votes_en': format_decimal(sd['votes'], locale='en_CA'),
                        'votes_fr': format_decimal(sd['votes'], locale='fr_CA'),
                        'keywords_en_text': str(sd['keywords_en']).split(","),
                        'keywords_eng': sd['keywords_en'],
                        'keywords_fr_text': str(sd['keywords_fr']).split(","),
                        'keywords_fra': sd['keywords_fr'],
                        'subject': str(sd['subject']).split(','),
                        'subject_en': [],
                        'subject_fr': [],
                        'comments_en_s': sd['additional_comments_and_feedback_en'],
                        'comments_fr_s': sd['additional_comments_and_feedback_fr'],
                        'suggestion_id': sd['suggestion_id'],
                        'reason': sd['reason'] if sd['reason'] else '-',
                        'reason_en': self.field_codes['reason'][sd['reason']].label_en if sd['reason'] else '-',
                        'reason_fr': self.field_codes['reason'][sd['reason']].label_fr if sd['reason'] else '-',
                        'date_created': date_created.isoformat() + "Z",
                        'date_created_en': format_date(date_created, locale='en'),
                        'date_created_fr': format_date(date_created, locale='fr'),
                        'date_forwarded': date_forwarded.isoformat() + "Z",
                        'date_forwarded_en': format_date(date_forwarded, locale='en'),
                        'date_forwarded_fr': format_date(date_forwarded, locale='fr'),
                    }

                    # Set the S.D. Subject(s)
                    solr_rec['subject_en'] = []
                    solr_rec['subject_fr'] = []
                    for subject in solr_rec['subject']:
                        solr_rec['subject_en'].append(self.field_codes['subject'][subject].label_en)
                        solr_rec['subject_fr'].append(self.field_codes['subject'][subject].label_fr)
                    solr_rec['subject_fra'] = ",".join(solr_rec['subject_fr'])
                    solr_rec['subject_eng'] = ",".join(solr_rec['subject_en'])

                    # Date released is an optional field. If it is not set in Drupal then this is signified in the
                    # application by setting the release data to 2000-01-01
                    solr_rec['date_released'] = date_released.isoformat() + "Z"
                    if date_released > datetime(2000, 1, 1):
                        solr_rec['date_released_en'] = format_date(date_released, locale='en')
                        solr_rec['date_released_fr'] = format_date(date_released, locale='fr')
                    else:
                        solr_rec['date_released_en'] = "-"
                        solr_rec['date_released_fr'] = "-"

                    # Update status handling - initialize some value then iterate through all the updates from the
                    # corresponding CKAN S.D. record. There will always be at least 1 update record

                    status_update_reason = []
                    status_update_reason_en = []
                    status_update_reason_fr = []
                    status_update_dates = []
                    status_update_dates_en = []
                    status_update_dates_fr = []
                    status_update_comments_en = []
                    status_update_comments_fr = []

                    last_status_date = datetime(2000, 1, 1)
                    for status in self.ckan_ds_status[sd['uuid']]['status']:
                        try:
                            # Date update was made
                            status_updated = datetime.strptime(status['date'], '%Y-%m-%d')
                            status_update_dates.append(status_updated.isoformat() + "Z")
                            status_update_dates_en.append(format_date(status_updated, locale='en'))
                            status_update_dates_fr.append(format_date(status_updated, locale='fr'))

                            # Optional comment on the update
                            if "comments" in status and 'en' in status['comments']:
                                status_update_comments_en.append(status['comments']['en'])
                            else:
                                status_update_comments_en.append('-')
                            if "comments" in status and 'fr' in status['comments']:
                                status_update_comments_fr.append(status['comments']['fr'])
                            else:
                                status_update_comments_fr.append('-')

                            # Reason for the update
                            status_update_reason.append(status['reason'])
                            status_update_reason_en.append(self.field_codes['status_update_reason'][status['reason']].label_en)
                            status_update_reason_fr.append(self.field_codes['status_update_reason'][status['reason']].label_fr)

                            # Set the overall S.D. status - which is typically the last update
                            if status_updated > last_status_date:
                                last_status_date = status_updated
                                solr_rec['status_en'] = self.field_codes['status_update_reason'][status['reason']].label_en
                                solr_rec['status_fr'] = self.field_codes['status_update_reason'][status['reason']].label_fr
                                solr_rec['status'] = status['reason']

                        except (ValueError, TypeError):
                            self.logger.warning(f"Bad status date '{status['date']}' for suggestion ID {sd['suggestion_id']}")
                    solr_rec['status_update_reason'] = status_update_reason
                    solr_rec['status_update_reason_en'] = status_update_reason_en
                    solr_rec['status_update_reason_eng'] = ",".join(status_update_reason_en)
                    solr_rec['status_update_reason_fr'] = status_update_reason_fr
                    solr_rec['status_update_reason_fra'] = ",".join(status_update_reason_fr)
                    solr_rec['status_update_dates'] = status_update_dates
                    solr_rec['status_update_dates_eng'] = status_update_dates_en
                    solr_rec['status_update_dates_en'] = ",".join(status_update_dates_en)
                    solr_rec['status_update_dates_fra'] = status_update_dates_fr
                    solr_rec['status_update_dates_fr'] = ",".join(status_update_dates_fr)
                    solr_rec['status_update_comments_en'] = status_update_comments_en
                    solr_rec['status_update_comments_eng'] = ",".join(status_update_comments_en)
                    solr_rec['status_update_comments_fr'] = status_update_comments_fr
                    solr_rec['status_update_comments_fra'] = ",".join(status_update_comments_fr)
                    solr_items.append(solr_rec)

            # Commit the update to Solr - because the number of S.D. is fairly small, this is done in one attempt.
            if len(solr_items) > 0:
                # try to connect to Solr up to 10 times
                for countdown in reversed(range(10)):
                    try:
                        solr.index(self.solr_core, solr_items)
                        self.logger.info(f"Rows committed to Solr: {len(solr_items)}")
                        solr_items.clear()
                        break
                    except ConnectionError as cex:
                        if not countdown:
                            raise
                        self.logger.info("Solr error: {0}. Waiting to try again ... {1}".format(cex, countdown))
                        time.sleep((10 - countdown) * 5)

            solr.commit(self.solr_core, softCommit=True, waitSearcher=True)
            self.logger.level = logging.INFO

        except Exception as x:
            traceback.print_exception(type(x), x, x.__traceback__)
            self.logger.error('Unexpected Error "{0}"'.format(x))
