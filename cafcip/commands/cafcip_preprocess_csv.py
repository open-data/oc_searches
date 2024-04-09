from django.core.management.base import BaseCommand
import csv
import logging
import pandas as pd
import sqlite3

class Command(BaseCommand):
    help = 'Process the DND IP Tracker data for loading into Solr'
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, help='The CSV file to be processed', required=True)
        parser.add_argument('--out', type=str, help='The processed CSV file', required=True)

    def handle(self, *args, **options):

        # Set up a temp Sqlite3 db to hold the content
        conn = sqlite3.connect("cafcip_temp_db.sqlite3")
        cur = conn.cursor()
        cur.execute("pragma max_page_count = 2147483646")
        cur.execute("VACUUM")
        cur.execute("PRAGMA synchronous = FULL")
        cur.execute("PRAGMA journal_mode = DELETE")

    # Process the records in the CSV file one at a time
        cur.execute(f'DROP TABLE IF EXISTS cafcip')
        cur.execute(f'DROP TABLE IF EXISTS latest')
        cur.execute('create table latest(cip_serial NVARCHAR, reporting_period NVARCHAR)')
        try:
            for chunk in pd.read_csv(options['csv'], chunksize=500, delimiter=",", dialect=csv.excel, encoding_errors='replace'):
                chunk.columns = chunk.columns.str.replace(' ', '_')  # replacing spaces with underscores for column names
                chunk.to_sql(name="cafcip", con=conn, if_exists='append')

            cur.execute("insert into latest select cip_serial, max(reporting_period) from cafcip group by cip_serial")
            cur.execute("commit")

            cur.execute("select l.reporting_period, n.reporting_period, n.cip_serial, n.record_no, n.report, n.phase, n.completion_date, n.short_desc_en, n.short_desc_fr, n.desc_en, n.desc_fr, n.culture_aspect, n.status, n.context_en, n.context_fr, n.status_comments_en, n.status_comments_fr, n.web_links_en1, n.web_links_en2, n.web_links_en3, n.web_links_en4, n.web_links_fr1, n.web_links_fr2, n.web_links_fr3, n.web_links_fr4, n.actual_date from cafcip n join latest l on n.cip_serial = l.cip_serial")
            cafcip_data = cur.fetchall()

            with open(options['out'], 'w', newline='', encoding='utf-8-sig') as outfile:
                out_writer = csv.writer(outfile, dialect='excel', )
                out_writer.writerow(['reporting_period', 'cip_serial', 'record_no', 'report', 'phase', 'completion_date', 'short_desc_en', 'short_desc_fr', 'desc_en', 'desc_fr', 'culture_aspect', 'status', 'context_en', 'context_fr', 'status_comments_en', 'status_comments_fr', 'web_links_en1', 'web_links_en2', 'web_links_en3', 'web_links_en4', 'web_links_fr1', 'web_links_fr2', 'web_links_fr3', 'web_links_fr4', 'actual_date', 'is_latest'])
                for dt in cafcip_data:
                    row = list(dt)
                    if row[0] == row[1]:
                        row.append('T')
                    else:
                        row.append('F')
                    del row[0]
                    out_writer.writerow(row)

        except Exception as e:
            self.logger.critical(f'Error processing')
            self.logger.error(e)

        finally:
            cur.execute('VACUUM')
            conn.close()
