import csv
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from email.message import EmailMessage
from email.headerregistry import Address
from email_validator import validate_email, EmailNotValidError
import json
import logging
from os import path
import smtplib
from search.models import Search
from SolrClient import SolrClient
from SolrClient.exceptions import ConnectionError

EMAIL_HTML_TEMPLATE = """
<html>
<head></head>
<body>
<p>This is an automated message, and replies are not monitored. For help or more information, please contact <a href="mailto:open-ouvert@tbs-sct.gc.ca">open-ouvert@tbs-sct.gc.ca</a>.</p>
<br>
<p>Good day,</p>
<p>Your ‘Suggest a Dataset’ submission on open.canada.ca has an update!</p>
<p>Access it here: {0}</p>
<p>Leave feedback or ask questions using the Comment feature, found on the bottom of the page.</p>
<p>Have another idea for a dataset?  Use our <a href="https://open.canada.ca/en/suggested-datasets">‘Suggest a Dataset Form’</a> to submit your suggestions!</p>
<br>
<p>Thank you,<br>The Open Government Team</p>

<hr>

<p>Ceci est un message automatisé, et les réponses ne sont pas surveillées. Pour obtenir de l'aide ou de plus amples renseignements, veuillez communiquer avec <a href="mailto:open-ouvert@tbs-sct.gc.ca">open-ouvert@tbs-sct.gc.ca</a>.</p>
<br>
<p>Bonjour.</p>
<p>Une mise à jour est disponible concernant la proposition d’un jeu de données que vous avez faite sur ouvert.canada.ca!</p>
<p>Pour y accéder, veuillez suivre le lien suivant : {1}</p>
<p>Pour tout commentaire ou toute question, veuillez cliquer sur le bouton « Commentaire » au bas de la page.</p>
<p>Vous avez un autre jeu de données à proposer? Soumettez-le-nous à l’aide du <a href="">«Formulaire de proposition d’un jeu de données!»</a></p>
<br>
<p>Cordialement,<br>L’équipe du gouvernement ouvert</p>
</body>
</html>
"""

EMAIL_TEXT_TEMPLATE = """
This is an automated message, and replies are not monitored. For help or more information, please contact open-ouvert@tbs-sct.gc.ca.


Good day,

Your ‘Suggest a Dataset’ submission on open.canada.ca has an update!

Access it here: {0}

Leave feedback or ask questions using the Comment feature, found on the bottom of the page.

Have another idea for a dataset?  Use our ‘Suggest a Dataset Form’ to submit your suggestions!

https://open.canada.ca/en/suggested-datasets


Thank you,

The Open Government Team

---

Ceci est un message automatisé, et les réponses ne sont pas surveillées. Pour obtenir de l'aide ou de plus amples renseignements, veuillez communiquer avec open-ouvert@tbs-sct.gc.ca.


Bonjour.

Une mise à jour est disponible concernant la proposition d’un jeu de données que vous avez faite sur ouvert.canada.ca!

Pour y accéder, veuillez suivre le lien suivant : {1}

Pour tout commentaire ou toute question, veuillez cliquer sur le bouton « Commentaire » au bas de la page.

Vous avez un autre jeu de données à proposer? Soumettez-le-nous à l’aide du «Formulaire de proposition d’un jeu de données!»

https://ouvert.canada.ca/fr/jeux-de-donnees-suggeres


Cordialement,

L’équipe du gouvernement ouvert

"""


class Command(BaseCommand):

    help = 'Check for a status update by comparing the Drupal CSV file with Solr'

    logger = logging.getLogger('ogc_search')

    def add_arguments(self, parser):
        parser.add_argument('--drupal_csv', type=str, required=True)
        parser.add_argument('--ckan_json', type=str, required=True)
        parser.add_argument('--search', type=str, help='The Search ID that is being loaded', required=True)

    def handle(self, *args, **options):

        solr = SolrClient(settings.SOLR_SERVER_URL)
        search_target = Search.objects.get(search_id=options['search'])
        solr_core = search_target.solr_core_name

        # Verify Drupal file
        if not path.exists(options['drupal_csv']):
            raise CommandError('Druapl CSV file not found: ' + options['drupal_csv'])

        # Verify CKAN file
        if not path.exists(options['ckan_json']):
            raise CommandError('CKAN JSON file not found: ' + options['ckan_json'])

        ckan_status = {}
        with open(options['ckan_json'], 'r', encoding='utf-8', errors="ignore") as ckan_file:
            self.logger.info("Processing " + options['ckan_json'])
            records = ckan_file.readlines()
            for record in records:
                ds = json.loads(record)
                # Assumption made here that the mandatory 'id', 'status', and 'date_forwarded' fields are present

                last_status_date = datetime(2000, 1, 1)
                current_status = ''
                if 'status' in ds:
                    for status_update in ds['status']:
                        status_date = datetime.strptime(status_update['date'], '%Y-%m-%d')
                        if status_date > last_status_date:
                            last_status_date = status_date
                            current_status = status_update['reason']
                    ckan_status[ds['id']] = current_status

        with open(options['drupal_csv'], 'r', encoding='utf-8-sig', errors="ignore") as sd_file:
            sd_reader = csv.DictReader(sd_file, dialect='excel')
            self.logger.info("Processcing " + options['drupal_csv'])
            for sd in sd_reader:
                if sd['email']:
                    try:
                        # Check for valid email before proceeding
                        valid = validate_email(sd['email'])
                        submitter_email = valid.email

                        # Check Solr for old status code
                        solr_query = {'q': f"id:{sd['uuid']}", 'defType': 'edismax', 'sow': True, 'start': 0, 'rows': 1, 'sort': "id asc"}
                        results = solr.query(solr_core, solr_query)
                        if len(results.docs) == 1:
                            old_status = results.docs[0]['status']

                            # Compare against new status from CKAN
                            if sd['uuid'] in ckan_status:
                                self.logger.info("CKAN ID: {0}, New Status: {1}, Old Status: {2}".format(sd['uuid'], ckan_status[sd['uuid']], old_status))
                                if ckan_status[sd['uuid']] != old_status and  ckan_status[sd['uuid']] != "":
                                    self.logger.info("Status change detected for " + sd['uuid'])

                                    # Send an email
                                    status_email = EmailMessage()
                                    status_email['Subject'] = "Status update to your suggested dataset / L’équipe du gouvernement ouvert"

                                    # By design, don't send HTML email to own corporate domain
                                    if 'tbs-sct.gc.ca' == valid.domain:
                                        status_email['From'] = settings.SD_ALERT_EMAIL_FROM[0]
                                        status_email["To"] = submitter_email
                                        status_email.set_content(EMAIL_TEXT_TEMPLATE.format(settings.SD_RECORD_URL_EN + sd['uuid'],
                                                                                            settings.SD_RECORD_URL_FR + sd['uuid']))

                                    else:
                                        status_email['From'] = Address(settings.SD_ALERT_EMAIL_FROM[0], settings.SD_ALERT_EMAIL_FROM[1], settings.SD_ALERT_EMAIL_FROM[2])
                                        status_email["To"] = Address(submitter_email, valid.local_part, valid.domain)
                                        status_email.set_content(EMAIL_TEXT_TEMPLATE.format(settings.SD_RECORD_URL_EN + sd['uuid'],
                                                                                            settings.SD_RECORD_URL_FR + sd['uuid']))
                                        status_email.add_alternative(EMAIL_HTML_TEMPLATE.format(settings.SD_RECORD_URL_EN + sd['uuid'],
                                                                                                settings.SD_RECORD_URL_FR + sd['uuid']),
                                                                     subtype="html")
                                    self.logger.info(status_email)
                                    with smtplib.SMTP("localhost") as mail:
                                        mail.send_message(status_email)
                        else:
                            # the record does not exist in Solr, so no further acton is possible
                            self.logger.info("No record found in Solr for " + sd['uuid'])
                            pass

                    except EmailNotValidError as e:
                        # The recipient's email address is not valid so no further action is possible
                        self.logger.info(e)
                        pass
