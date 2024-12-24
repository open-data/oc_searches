from babel.numbers import format_decimal
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

AMENDMENTS_HEADERS = CONTRACTS_HEADERS + ",amendment_no,procurement_count,aggregate_total,pseudo_procurement_id"


class Command(BaseCommand):
    help = ('Django manage command that tries to match individual contract records into contracts and amendments '
            'for use with Search')

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--contracts', type=str, help='Contracts CSV input file', required=True)
        parser.add_argument('--amendments', type=str, help='Amendments CSV output file', required=True)
        parser.add_argument('--tmpdir', type=str, default=os.getcwd(), help="Working directory to create the sqlite3 db", required=False)
        parser.add_argument('--round2', required=False, action='store_true', help="Perform round 2 matching")

    def handle(self, *args, **options):

        if not os.path.exists(options['contracts']):
            raise CommandError(f'Contracts file {options["contracts"]} does not exist')

        if not os.path.exists(options['tmpdir']):
            raise CommandError(f'Working directory {options["tmpdir"]} does not exist')

        if os.path.exists(options['amendments']):
            print(f"Amendments file {options['amendments']} already exists, removing...")
            os.remove(options['amendments'])

        # Delete the sqllite DB File - always start with a clean database
        db_path = os.path.join(options['tmpdir'], "contracts.sqlite3")
        if os.path.exists(db_path):
            os.remove(db_path)

        sqldb = sqlite3.connect(db_path)
        sql_cursor = sqldb.cursor()

        # Load the contracts PD CSV file into a SQLite3 database for easier manipulation

        with open(options['contracts'], 'r', encoding='utf-8-sig', errors="xmlcharrefreplace") as csv_file:
            csv_reader = csv.DictReader(csv_file, dialect='excel')

            # Create a table to hold the original contract values
            sql_cursor.execute(f"CREATE TABLE IF NOT EXISTS contracts({CONTRACTS_HEADERS.replace(',',' text, ')} text)")

            # Create a table to hold the pass 1 and 2 amendment values
            sql_cursor.execute(f"CREATE TABLE IF NOT EXISTS amendments({AMENDMENTS_HEADERS.replace(',',' text, ')} text)")

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
            sql_cursor.execute('CREATE INDEX proc_idx ON contracts (owner_org, procurement_id)')
            sql_cursor.execute('CREATE INDEX inst_idx ON contracts (owner_org, procurement_id, instrument_type)')

        sqldb.commit()
        sql_cursor.execute("SELECT COUNT(*) FROM contracts")
        count = sql_cursor.fetchone()[0]
        print(f"{count} contracts records loaded")

        #  PASS 1 - Match contracts to amendments using owner-org, procurement ID, and instrument type

        last_key = ""
        amend_no = 0
        sql_cursor_count = sqldb.cursor()
        sql_cursor_2 = sqldb.cursor()
        pass1_count = 0
        pass1_contract = 0
        record_cnt = 0
        grand_total = 0

        # Cycle through the contracts and if conditions are met, set the search-only amendment fields which the
        # Search application will use in its UI to group amendments with contracts
        if os.path.exists('pass1_report.csv'):
            os.remove('pass1_report.csv')
        with open('pass1_report.csv', 'a', encoding='utf-8-sig') as csv_out:
            report_writer = csv.DictWriter(csv_out, fieldnames=AMENDMENTS_HEADERS.split(","), delimiter=',', restval='', extrasaction='ignore', lineterminator='\n')
            report_writer.writeheader()
            for row in sql_cursor.execute(f"SELECT {CONTRACTS_HEADERS} FROM contracts ORDER BY owner_org ASC, procurement_id ASC, instrument_type DESC, reporting_period ASC"):

                # When the key changes, s new contract has started
                is_pass1_record = False
                current_key = f"{row[41]},{row[1]}"
                if current_key != last_key:
                    amend_no = 0
                else:
                    amend_no += 1
                last_key = current_key

                # Create a amendments dict for populating the amendments table. Set the search-only amendment fields
                amend_dict = {}
                for i, key in enumerate(CONTRACTS_HEADERS.split(",")):
                    amend_dict[key] = row[i]
                amend_dict["amendment_no"] = amend_no
                amend_dict["aggregate_total"] = 0
                proc_count = sql_cursor_count.execute("SELECT COUNT(*) FROM contracts WHERE owner_org = ? AND procurement_id = ?", (row[41], row[1])).fetchone()[0]
                non_contracts_count = sql_cursor_count.execute("SELECT COUNT(*) FROM contracts WHERE owner_org = ? AND procurement_id = ? AND instrument_type <> 'C'", (row[41], row[1])).fetchone()[0]
                contracts_count = sql_cursor_count.execute("SELECT COUNT(*) FROM contracts WHERE owner_org = ? AND procurement_id = ? AND instrument_type = 'C'", (row[41], row[1])).fetchone()[0]

                # There needs to be at least 1 amendment AND 1 contract for this contact/amendment matching logic to apply
                pass1_flag = False
                if non_contracts_count > 0 and contracts_count == 1:
                    for val_row in sql_cursor_count.execute("SELECT original_value, amendment_value from contracts WHERE owner_org = ? and procurement_id = ? and instrument_type = ?",(row[41], row[1], "C")):
                        if val_row[1] not in ["", "0", "0.0"]:
                            print(f"The original contract record for {row[41]},{row[1]} has an unexpected amendment value {val_row[1]}")
                        else:
                            pass1_flag = True
                if pass1_flag:
                    pass1_count += 1
                    is_pass1_record = True
                    amend_dict['procurement_count'] = proc_count
                    if row[34] == 'C' or row[34] == 'SOSA':
                        grand_total = 0.0
                        pass1_contract += 1
                        for pro_row in sql_cursor_2.execute("SELECT instrument_type, original_value, amendment_value from contracts WHERE owner_org = ? and procurement_id = ?",(row[41], row[1])):
                            try:
                                if pro_row[0] == "C":
                                    if pro_row[1]:
                                        grand_total += float(pro_row[1])
                                else:
                                    if pro_row[2]:
                                        grand_total += float(pro_row[2])
                            except ValueError as ve:
                                print(f"Bad numbers: original value {pro_row[1]}, amendment value {pro_row[2]}: {row[41]},{row[1]}")
                        amend_dict['aggregate_total'] = format_decimal(grand_total, locale='en_US')
                # Pass 1 logic does not apply, continue treating the current record as an individual record
                else:
                    amend_dict["amendment_no"] = 0
                    amend_dict['procurement_count'] = 1
                    amend_dict['aggregate_total'] = row[11]

                # In order to support both pass 1 and pass 2, the Search UI uses a procurement id placeholder instead of the original orocurement id.
                amend_dict['pseudo_procurement_id'] = amend_dict['procurement_id']

                # Save the pass 1 data to the amendments table
                sql_cursor_2.execute('INSERT INTO amendments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                   (amend_dict["reference_number"],
                                    amend_dict["procurement_id"],
                                    amend_dict["vendor_name"],
                                    amend_dict["vendor_postal_code"],
                                    amend_dict["buyer_name"],
                                    amend_dict["contract_date"],
                                    amend_dict["economic_object_code"],
                                    amend_dict["description_en"],
                                    amend_dict["description_fr"],
                                    amend_dict["contract_period_start"],
                                    amend_dict["delivery_date"],
                                    amend_dict["contract_value"],
                                    amend_dict["original_value"],
                                    amend_dict["amendment_value"],
                                    amend_dict["comments_en"],
                                    amend_dict["comments_fr"],
                                    amend_dict["additional_comments_en"],
                                    amend_dict["additional_comments_fr"],
                                    amend_dict["agreement_type_code"],
                                    amend_dict["trade_agreement"],
                                    amend_dict["land_claims"],
                                    amend_dict["commodity_type"],
                                    amend_dict["commodity_code"],
                                    amend_dict["country_of_vendor"],
                                    amend_dict["solicitation_procedure"],
                                    amend_dict["limited_tendering_reason"],
                                    amend_dict["trade_agreement_exceptions"],
                                    amend_dict["indigenous_business"],
                                    amend_dict["indigenous_business_excluding_psib"],
                                    amend_dict["intellectual_property"],
                                    amend_dict["potential_commercial_exploitation"],
                                    amend_dict["former_public_servant"],
                                    amend_dict["contracting_entity"],
                                    amend_dict["standing_offer_number"],
                                    amend_dict["instrument_type"],
                                    amend_dict["ministers_office"],
                                    amend_dict["number_of_bids"],
                                    amend_dict["article_6_exceptions"],
                                    amend_dict["award_criteria"],
                                    amend_dict["socioeconomic_indicator"],
                                    amend_dict["reporting_period"],
                                    amend_dict["owner_org"],
                                    amend_dict["owner_org_title"],
                                    amend_dict["amendment_no"],
                                    amend_dict['procurement_count'],
                                    amend_dict['aggregate_total'],
                                    amend_dict['pseudo_procurement_id']
                                    ))
                if is_pass1_record:
                    report_writer.writerow(amend_dict)
            csv_out.close()

        sql_cursor.execute('CREATE INDEX IF NOT EXISTS proc2_idx ON amendments (owner_org, procurement_id)')
        sql_cursor.execute('CREATE INDEX IF NOT EXISTS inst2_idx ON amendments (owner_org, procurement_id, instrument_type)')
        sql_cursor.execute('CREATE INDEX IF NOT EXISTS inst3_idx ON amendments (vendor_name, contract_date, economic_object_code, owner_org, procurement_id, instrument_type)')
        sql_cursor.execute('CREATE INDEX IF NOT EXISTS proc4_idx ON amendments (owner_org, reference_number)')
        sqldb.commit()

        print(f"Pass 1: {pass1_count} records matched to {pass1_contract} contracts based on procurement ID")

        # Pass 2 Matching -- optional
        if options["round2"]:
            pass2_count = 0
            pass2_contracts = 0

            if os.path.exists('pass2_report.csv'):
                os.remove('pass2_report.csv')
            with open('pass2_report.csv', 'a', encoding='utf-8-sig') as csv_out:
                # report_writer = csv.DictWriter(csv_out, fieldnames="owner_org,reference_number,instrument_type,procurement_id,vendor_name,contract_date,economic_object_code,pseudo_procurement_id".split(","), delimiter=',', restval='', extrasaction='ignore', lineterminator='\n')
                report_writer = csv.DictWriter(csv_out, fieldnames=AMENDMENTS_HEADERS.split(","), delimiter=',', restval='', extrasaction='ignore', lineterminator='\n')
                report_writer.writeheader()

                for a_row in sql_cursor.execute("select count(*) as cnt, vendor_name, contract_date, economic_object_code, owner_org  from amendments group by vendor_name, contract_date, economic_object_code, owner_org order by cnt desc"):
                    # Don't need to consider single records or records that were already matched in Pass 1
                    if a_row[0] <= 1:
                        break
                    amendment_no = 0
                    procurement_count = a_row[0]
                    aggregate_total = 0.0
                    # No. of Contract records in the group
                    c_count = sql_cursor_count.execute('SELECT count(*) FROM amendments WHERE vendor_name = ? AND contract_date = ? AND economic_object_code = ? AND owner_org = ? AND procurement_count = 1 and instrument_type = "C"',
                                                   (a_row[1], a_row[2], a_row[3], a_row[4])).fetchone()[0]
                    # No. of Amendment records in the group
                    a_count = sql_cursor_count.execute('SELECT count(*) FROM amendments WHERE vendor_name = ? AND contract_date = ? AND economic_object_code = ? AND owner_org = ? AND procurement_count = 1 and instrument_type = "A"',
                                                   (a_row[1], a_row[2], a_row[3], a_row[4])).fetchone()[0]

                    if c_count == 1 and a_count > 0:
                        pass2_contracts += 1
                        # Do two passes, one to get the total AND to make sure the first record is either a contract or a SO any subsequent records are amendments
                        # Step 1 - validated Contract/Amendment instrument type is correct, and calculate the aggregate total
                        grand_total = 0.0
                        is_valid = True
                        i = 0
                        k = 0
                        for g_row in sql_cursor_2.execute("select instrument_type, original_value, amendment_value from amendments where vendor_name = ? AND contract_date = ? AND economic_object_code = ? AND owner_org = ? AND procurement_count = 1 ORDER BY reporting_period ASC, reference_number ASC",
                                                          (a_row[1], a_row[2], a_row[3], a_row[4])):
                            # IF the first record is not a contract or standing offer then this group cannot be considered for pass 2
                            if i == 0 and g_row[0] not in ('C', 'SOSA'):
                                is_valid = False
                                break
                            try:
                                if g_row[0] == "C":
                                    if g_row[1]:
                                        grand_total += float(g_row[1])
                                else:
                                    if g_row[2]:
                                        grand_total += float(g_row[2])

                            except ValueError as ve:
                                print(f"Bad numbers: original value {g_row[1]}, amendment value {g_row[2]}: {a_row[4]},{a_row[1]}")
                            i += 1
                            k += 1

                        # Step 2 - Update validated groups with amendment information

                        if is_valid:
                            i = 0
                            psuedo_proc = ""
                            for g_row in sql_cursor_2.execute("SELECT owner_org, reference_number, instrument_type, procurement_id from amendments WHERE vendor_name = ? AND contract_date = ? AND economic_object_code = ? AND owner_org = ? AND procurement_count = 1 ORDER BY reporting_period ASC, reference_number ASC",
                                                                (a_row[1], a_row[2], a_row[3], a_row[4])):
                                sql_cursor_update = sqldb.cursor()

                                if i == 0:
                                    psuedo_proc = f"{g_row[3]}_{g_row[0]}_{a_row[2]}"

                                if g_row[2] in ('C', 'SOSA'):
                                    sql_cursor_update.execute('UPDATE amendments SET aggregate_total = ?, amendment_no = ?, procurement_count = ?, pseudo_procurement_id = ? WHERE owner_org = ? AND reference_number = ?',
                                                         (grand_total, i, k, psuedo_proc, a_row[4], g_row[1]))
                                else:
                                    sql_cursor_update.execute('UPDATE amendments SET  amendment_no = ?, procurement_count = ?, pseudo_procurement_id = ? WHERE owner_org = ? AND reference_number = ?',
                                                         (i, k, psuedo_proc, a_row[4], g_row[1]))
                                i += 1
                                pass2_count += 1
                                sqldb.commit()
                                sql_cursor_pass2 = sqldb.cursor()
                                pass2_dict = {}
                                for p2_row in sql_cursor_pass2.execute(f"SELECT {AMENDMENTS_HEADERS} from amendments where owner_org = ? AND reference_number = ?", (a_row[4], g_row[1])):
                                    for i, key in enumerate(AMENDMENTS_HEADERS.split(",")):
                                        pass2_dict[key] = p2_row[i]
                                    report_writer.writerow(pass2_dict)

                print(f"Pass 2: {pass2_count} additional records matched as {pass2_contracts} amended contracts")
                sqldb.commit()

        # Write out amendments to CSV ready to be imported into Search
        with open(options['amendments'], 'a', encoding='utf-8-sig') as csv_out:
            csv_writer = csv.DictWriter(csv_out, fieldnames=AMENDMENTS_HEADERS.split(","), delimiter=',', restval='', extrasaction='ignore', lineterminator='\n')
            csv_writer.writeheader()
            for row in sql_cursor.execute(f"SELECT {AMENDMENTS_HEADERS} FROM amendments ORDER BY owner_org ASC, pseudo_procurement_id ASC, instrument_type DESC, reporting_period ASC"):
                amend_dict = {}
                for i, key in enumerate(AMENDMENTS_HEADERS.split(",")):
                    amend_dict[key] = row[i]
                csv_writer.writerow(amend_dict)
                record_cnt += 1
            print(f"{record_cnt} records exported to CSV")
        sqldb.close()

