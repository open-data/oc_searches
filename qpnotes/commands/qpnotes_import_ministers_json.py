from datetime import datetime, timezone
from django.core.management.base import BaseCommand, CommandError
import json
import logging
from os import path
from search.models import Code, Field, Search, ChronologicCode
import pytz


class Command(BaseCommand):

    help = 'Django manage command to import Minister title codes from a JSON file for the QP Notes search'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--json_file', type=str, help='Ministers JSON file name', required=True)
        parser.add_argument('--search', type=str, help='A unique code identifier for the Search', required=True)
        parser.add_argument('--flush', action='store_true', help='Flush existing data before loading', default=True)

    def handle(self, *args, **options):
        local_tz = "US/Eastern"

        if not path.exists(options['json_file']):
            raise CommandError('JSON file not found: ' + options['json_file'])

        with open(options['json_file'], 'r', encoding='utf8') as fp:

            c_count = 0
            c_count_new = 0
            cc_count = 0
            cc_count_new = 0
            search = Search.objects.get(search_id=options['search'])
            choices = json.load(fp)
            field = Field.objects.get(field_id='minister', search_id=search)

            # Remove existing data if requested
            if options['flush']:
                self.logger.info('Flushing existing data')
                codes = Code.objects.filter(field_id=field)
                for code in codes:
                    ChronologicCode.objects.filter(code_id=code).delete()

            for choice in choices:
                code, created = Code.objects.get_or_create(field_id_id=field.id, code_id=choice)
                code.label_en = choices[choice]['en']
                code.label_fr = choices[choice]['fr']
                code.save()
                c_count += 1
                if created:
                    c_count_new += 1

                for minister in choices[choice]['ministers']:
                    start_date = datetime.strptime(minister['start_date'], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=pytz.timezone(local_tz))
                    if not minister['end_date'] == "":
                        end_date = datetime.strptime(minister['end_date'], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=pytz.timezone(local_tz))
                    else:
                        end_date = datetime(2999, 12, 31).replace(tzinfo=pytz.timezone(local_tz))
                    chronocode, created = ChronologicCode.objects.get_or_create(code_id_id=code.id,
                                                                                start_date=start_date)
                    chronocode.label = minister['name']
                    chronocode.label_en = minister['name_en']
                    chronocode.label_fr = minister['name_fr']
                    chronocode.end_date = end_date
                    chronocode.save()
                    cc_count += 1
                    if created:
                        cc_count_new += 1

            self.logger.info("Loaded {0} ministers ({1} new), and {2} names ({3} new)".format(c_count, c_count_new,
                                                                                                  cc_count, cc_count_new))
