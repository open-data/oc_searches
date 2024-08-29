from datetime import datetime, timezone
from types import new_class

from django.core.management.base import BaseCommand, CommandError
import logging
from os import path
from search.models import Code, Field, Search
import pytz
import yaml


class Command(BaseCommand):

    help = 'Django manage command to import Minister title codes from a JSON file for the QP Notes search'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--group_file', type=str, help='Group Classifications YAML file name', required=True)
        parser.add_argument('--search', type=str, help='A unique code identifier for the Search', required=True)
        parser.add_argument('--flush', action='store_true', help='Flush existing data before loading', default=True)

    def handle(self, *args, **options):
        local_tz = "US/Eastern"

        if not path.exists(options['group_file']):
            raise CommandError('Groups YAML file not found: ' + options['group_file'])

        results = []
        new_codes_deleted = 0
        old_codes_deleted = 0
        new_codes_updated = 0
        new_codes_created = 0
        old_codes_updated = 0
        old_codes_created = 0

        with open(options['group_file'], 'r', encoding='utf8') as fp:

            # Read in the groups YAML file
            groups = yaml.safe_load(fp)

            # Retrieve the Group Field objects that need the group code values
            search = Search.objects.get(search_id=options['search'])
            field_old_group = Field.objects.get(field_id='old_class_group_code', search_id=search)
            field_new_group = Field.objects.get(field_id='new_class_group_code', search_id=search)

            # Remove existing data if requested
            if options['flush']:
                self.logger.info('Removing previous Group codes')
                codes = Code.objects.filter(field_fid=field_old_group)
                for code in codes:
                    code.delete()
                    old_codes_deleted += 1
                if old_codes_deleted > 0:
                    results.append(f"{old_codes_deleted} Old Group Codes deleted")
                codes = Code.objects.filter(field_fid=field_new_group)
                for code in codes:
                    code.delete()
                    new_codes_deleted += 1
                if new_codes_deleted > 0:
                    results.append(f"{new_codes_deleted} New Group Codes deleted")

            for group in groups:

                # Add Old Classification codes

                code, created = Code.objects.get_or_create(field_fid=field_old_group, code_id=group)
                code.label_en = groups[group]['en']
                if 'fr' in groups[group]:
                    code.label_fr = groups[group]['fr']
                elif 'fR' in groups[group]:
                    code.label_fr = groups[group]['fR']
                code.save()
                if created:
                    old_codes_created += 1
                else:
                    old_codes_updated += 1

                # Add New Classification codes

                code, created = Code.objects.get_or_create(field_fid=field_new_group, code_id=group)
                code.label_en = groups[group]['en']
                if 'fr' in groups[group]:
                    code.label_fr = groups[group]['fr']
                elif 'fR' in groups[group]:
                    code.label_fr = groups[group]['fR']
                code.save()
                if created:
                    new_codes_created += 1
                else:
                    new_codes_updated += 1

        if old_codes_updated > 1:
            results.append(f"{old_codes_updated} Old Group Codes Updated")
        if old_codes_created > 0:
            results.append(f"{old_codes_created} Old Group Codes Created")
        if new_codes_updated > 0:
            results.append(f"{new_codes_updated} New Group Codes Updated")
        if new_codes_created > 0:
            results.append(f"{new_codes_created} New Group Codes Created")

        print(", ".join(results))
