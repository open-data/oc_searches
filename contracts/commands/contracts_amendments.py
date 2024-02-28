from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import csv
import logging
import os
import sqlite3

CONTRACTS_HEADERS = "reference_number,procurement_id,vendor_name,vendor_postal_code,buyer_name,contract_date," \
                    "economic_object_code,description_en,description_fr,contract_period_start,delivery_date," \
                    "contract_value,original_value,amendment_value,comments_en,comments_fr," \
                    "additional_comments_en,additional_comments_fr,agreement_type_code,trade_agreement," \
                    "land_claims,commodity_type,commodity_code,country_of_vendor,solicitation_procedure," \
                    "limited_tendering_reason,trade_agreement_exceptions,indigenous_business," \
                    "indigenous_business_excluding_psib,intellectual_property,potential_commercial_exploitation," \
                    "former_public_servant,contracting_entity,standing_offer_number,instrument_type," \
                    "ministers_office,number_of_bids,article_6_exceptions,award_criteria,socioeconomic_indicator," \
                    "reporting_period,owner_org,owner_org_title"

AMENDMENTS_HEADERS = CONTRACTS_HEADERS + ",amendment_no,procurement_count"


class Command(BaseCommand):
    help = 'Django manage command that will manage contracts amendments'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--contracts', type=str, help='Contracts CSV input file', required=True)
        parser.add_argument('--amendments', type=str, help='Amendments CSV output file', required=True)
        parser.add_argument('--reload', type=str, default='y', help="Recreate existing db files", required=False)

    def handle(self, *args, **options):

        if options['reload'] == "y":
            if not os.path.exists(options['contracts']):
                raise CommandError(f'Contracts file {options["contracts"]} does not exist')
            # Delete the sqllite DB File
            if os.path.exists("contracts.sqlite3"):
                os.remove("contracts.sqlite3")

        if os.path.exists(options['amendments']):
            print(f"Amendments file {options['amendments']} already exists, removing...")
            os.remove(options['amendments'])
        sqldb = sqlite3.connect("contracts.sqlite3")
        sql_cursor = sqldb.cursor()

        if options['reload'] == "y":
            with open(options['contracts'], 'r', encoding='utf-8-sig', errors="xmlcharrefreplace") as csv_file:
                csv_reader = csv.DictReader(csv_file, dialect='excel')
                sql_cursor.execute(
                    'CREATE TABLE contracts ('
                    'reference_number text, procurement_id text, vendor_name text, vendor_postal_code text, '
                    'buyer_name text, contract_date text, economic_object_code text, description_en text, '
                    'description_fr text, contract_period_start text, delivery_date text, contract_value text, '
                    'original_value text, amendment_value text, comments_en text, comments_fr text, '
                    'additional_comments_en text, additional_comments_fr text, agreement_type_code text, '
                    'trade_agreement text, land_claims text, commodity_type text, commodity_code text, '
                    'country_of_vendor text, solicitation_procedure text, limited_tendering_reason text, '
                    'trade_agreement_exceptions text, indigenous_business text, indigenous_business_excluding_psib text, '
                    'intellectual_property text, potential_commercial_exploitation text, former_public_servant text, '
                    'contracting_entity text, standing_offer_number text, instrument_type text, ministers_office text, '
                    'number_of_bids text, article_6_exceptions text, award_criteria text, socioeconomic_indicator text, '
                    'reporting_period text, owner_org text, owner_org_title text)')
                sql_cursor.execute('CREATE INDEX proc_idx ON contracts (owner_org, procurement_id)')
                for row_num, row in enumerate(csv_reader):
                    sql_cursor.execute('INSERT INTO contracts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                       (row["reference_number"],
                                         row["procurement_id"],
                                         row["vendor_name"],
                                         row["vendor_postal_code"],
                                         row["buyer_name"],
                                         row["contract_date"],
                                         row["economic_object_code"],
                                         row["description_en"],
                                         row["description_fr"],
                                         row["contract_period_start"],
                                         row["delivery_date"],
                                         row["contract_value"],
                                         row["original_value"],
                                         row["amendment_value"],
                                         row["comments_en"],
                                         row["comments_fr"],
                                         row["additional_comments_en"],
                                         row["additional_comments_fr"],
                                         row["agreement_type_code"],
                                         row["trade_agreement"],
                                         row["land_claims"],
                                         row["commodity_type"],
                                         row["commodity_code"],
                                         row["country_of_vendor"],
                                         row["solicitation_procedure"],
                                         row["limited_tendering_reason"],
                                         row["trade_agreement_exceptions"],
                                         row["indigenous_business"],
                                         row["indigenous_business_excluding_psib"],
                                         row["intellectual_property"],
                                         row["potential_commercial_exploitation"],
                                         row["former_public_servant"],
                                         row["contracting_entity"],
                                         row["standing_offer_number"],
                                         row["instrument_type"],
                                         row["ministers_office"],
                                         row["number_of_bids"],
                                         row["article_6_exceptions"],
                                         row["award_criteria"],
                                         row["socioeconomic_indicator"],
                                         row["reporting_period"],
                                         row["owner_org"],
                                         row["owner_org_title"]))

            sqldb.commit()
        sql_cursor.execute("SELECT COUNT(*) FROM contracts")
        count = sql_cursor.fetchone()[0]
        print(f"{count} contracts records loaded")
        last_key = ""
        amend_no = 0

        # @TODO Set up CSV OUTPUT file with the amendments column
        sql_cursor_1 = sqldb.cursor()
        with open(options['amendments'], 'a', encoding='utf-8-sig') as csv_out:
            csv_writer = csv.DictWriter(csv_out, fieldnames=AMENDMENTS_HEADERS.split(","), delimiter=',', restval='', extrasaction='ignore', lineterminator='\n')
            csv_writer.writeheader()
            amend_cnt = 0
            record_cnt = 0
            for row in sql_cursor.execute(f"SELECT {CONTRACTS_HEADERS} FROM contracts ORDER BY owner_org ASC, procurement_id ASC, instrument_type DESC, reporting_period ASC"):
                current_key = f"{row[41]},{row[1]}"
                if current_key != last_key:
                    amend_no = 0
                else:
                    amend_no = amend_no + 1
                    amend_cnt = amend_cnt + 1
                last_key = current_key
                # Create a regular dict for writing out
                amend_dict = {}
                for i, key in enumerate(CONTRACTS_HEADERS.split(",")):
                    amend_dict[key] = row[i]
                amend_dict["amendment_no"] = amend_no
                sql_cursor_1.execute("SELECT COUNT(*) FROM contracts WHERE owner_org = ? AND procurement_id = ?", (row[41], row[1]))
                amend_dict['procurement_count'] = sql_cursor_1.fetchone()[0]
                csv_writer.writerow(amend_dict)
                record_cnt = record_cnt + 1
                if record_cnt % 100000 == 0:
                    print(f"{record_cnt} records processed")
            print(f"{amend_cnt} amendments")
        sqldb.close()

