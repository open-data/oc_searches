from django.core.management.base import BaseCommand
from django.conf import settings
import json
import logging
from search.models import Search, Field, Code, Setting, SearchLog
from SolrClient import SolrClient
from SolrClient.exceptions import ConnectionError
from time import time
import traceback

class Command(BaseCommand):
    help = 'Validate Solr records against a remote CKAN instance'

    logger = logging.getLogger(__name__)
    # class variables that hold the search models
    search_target = None
    solr_core = None

    def add_arguments(self, parser):
        parser.add_argument('--search', type=str, help='The Search ID that is being loaded', required=True)

    def handle(self, *args, **options):

        try:
            # Retrieve the Search  and Field models from the database
            self.search_target = Search.objects.get(search_id=options['search'])
            self.solr_core = self.search_target.solr_core_name

            search_ids = []
            offset = 0
            try:
                # Retrieve the Search  and Field models from the database
                solr = SolrClient(settings.SOLR_SERVER_URL)
                q = {'q': '*', 'fl': 'id', 'rows': 100, 'start': offset}
                solr.query(self.solr_core, q)
            except Search.DoesNotExist as x:
                self.logger.error('Search not found: "{0}"'.format(x))
                exit(-1)
            except Field.DoesNotExist as x1:
                self.logger.error('Fields not found for search: "{0}"'.format(x1))

        except Exception as x:
            traceback.print_exception(type(x), x, x.__traceback__)
            self.logger.error('Unexpected Error "{0}"'.format(x))
