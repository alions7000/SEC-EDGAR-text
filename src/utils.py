"""
    secedgartext: extract text from SEC corporate filings
    Copyright (C) 2017  Alexander Ions

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import logging
import os
import sys
import shutil
import argparse
import re
from os import path
import socket
import time
import datetime
import json
import sqlite3
import multiprocessing as mp
from copy import copy


"""Parse the command line arguments
"""
companies_file_location = ''
single_company = ''
project_dir = path.dirname(path.dirname(__file__))
parser = argparse.ArgumentParser()
parser.add_argument('--storage', help='Specify path to storage location')
parser.add_argument('--write_sql', default=True, help='Save metadata to sqlite database? (Boolean)')
parser.add_argument('--company', help='CIK code specifying company for single-company download')
parser.add_argument('--companies_list', help='path of text file with all company CIK codes to download')
parser.add_argument('--filings', help='comma-separated list of SEC filings of interest (10-Q,10-K...)')
parser.add_argument('--documents')
parser.add_argument('--start', help='document start date passed to EDGAR web interface')
parser.add_argument('--end', help='document end date passed to EDGAR web interface')
parser.add_argument('--report_period', help='search pattern for company report dates, e.g. 2012, 201206 etc.')
parser.add_argument('--batch_signature')
parser.add_argument('--start_company', help='index number of first company to download from the companies_list file')
parser.add_argument('--end_company', help='index number of last company to download from the companies_list file')
parser.add_argument('--traffic_limit_pause_ms', help='time to pause between download attempts, to avoid overloading EDGAR server')
parser.add_argument('--multiprocessing_cores', help='number of processor cores to use')
args = parser.parse_args()

if args.storage:
    if not path.isabs(args.storage):
        args.storage = path.join(project_dir, args.storage)
else:
    args.storage = path.join(project_dir, 'output_files_examples')

args.write_sql = args.write_sql or True
if args.company:
    single_company = args.company
else:
    if args.companies_list:
        companies_file_location = os.path.join(project_dir, args.companies_list)
    else:
        companies_file_location = os.path.join(project_dir, 'companies_list.txt')

args.filings = args.filings or \
    input('Enter filings search text (default: 10-K,10-Q): ') or \
    '10-K,10-Q'
args.filings = re.split(',', args.filings)          # ['10-K','10-Q']

if '10-K' in args.filings:
    search_window_days = 365
else:
    search_window_days = 91
ccyymmdd_default_start = (datetime.datetime.now() - datetime.timedelta(days=
                      search_window_days)).strftime('%Y%m%d')
args.start = int(args.start or \
    input('Enter start date for filings search (default: ' +
          ccyymmdd_default_start + '): ') or \
             ccyymmdd_default_start)
ccyymmdd_default_end = (datetime.datetime.strptime(str(args.start), '%Y%m%d') +
                        datetime.timedelta(days=search_window_days)).strftime('%Y%m%d')
args.end = int(args.end or \
    input('Enter end date for filings search (default: ' +
          ccyymmdd_default_end + '): ') or \
            ccyymmdd_default_end)
if str(args.report_period).lower() == 'all':
    date_search_string = '.*'
else:
    date_search_string = str(
        args.report_period or
        input('Enter filing report period ccyy, ccyymm etc. (default: all periods): ') or
        '.*')


"""Set up the metadata database
"""
batch_start_time = datetime.datetime.utcnow()
batch_machine_id = socket.gethostname()

if args.write_sql:
    db_location = path.join(args.storage, 'metadata.sqlite3')
    sql_connection = sqlite3.connect(db_location)
    sql_cursor = sql_connection.cursor()
    sql_cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
            id integer PRIMARY KEY,
            batch_number integer NOT NULL,
            batch_signature text NOT NULL,
            batch_start_time datetime NOT NULL,
            batch_machine_id text,
            sec_cik text NOT NULL,
            company_description text,
            sec_company_name text,
            sec_form_header text,
            sec_period_of_report integer,
            sec_filing_date integer,
            sec_index_url text,
            sec_url text,
            metadata_file_name text,
            document_group text,
            section_name text,
            section_n_characters integer,
            section_end_time datetime,
            extraction_method text,
            output_file text,
            start_line text,
            end_line text,
            time_elapsed real)
            """)
    sql_connection.commit()
    query_result = sql_cursor.execute('SELECT max(batch_number) FROM metadata').fetchone()
    if query_result and query_result[0]:
        batch_number = query_result[0] + 1
    else:
        batch_number = 1
    # put a dummy line into the metadata table to 'reserve' a batch number:
    # prevents other processes running in parallel from taking the same batch_number
    sql_cursor.execute("""
        insert into metadata (batch_number, batch_signature,
        batch_start_time, sec_cik) values
        """ + " ('" + "', '".join([str(batch_number),
                           str(args.batch_signature or ''),
                           str(batch_start_time)[:-3],  # take only 3dp microseconds
                           'dummy_cik_code']) + "')")
    sql_connection.commit()
else:
    batch_number = 0


"""Set up numbered storage sub-directory for the current batch run
"""
storage_toplevel_directory = os.path.join(args.storage,
                                          'batch_' +
                                          format(batch_number, '04d'))

# (re-)make the storage directory for the current batch. This will delete
# any contents that might be left over from earlier runs, thus avoiding
# any potential duplication/overlap/confusion
if os.path.exists(storage_toplevel_directory):
    shutil.rmtree(storage_toplevel_directory)
os.makedirs(storage_toplevel_directory)




"""Set up logging
"""
# log_file_name = 'sec_extractor_{0}.log'.format(ts)
log_file_name = 'secedgartext_batch_%s.log' % format(batch_number, '04d')
log_path = path.join(args.storage, log_file_name)

logger = logging.getLogger('text_analysis')
# # set up the logger if it hasn't already been set up earlier in the execution run
logger.setLevel(logging.DEBUG)  # we have to initialise this top-level setting otherwise everything defaults to logging.WARN level
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s',
                              '%Y%m%d %H:%M:%S')

file_handler = logging.FileHandler(log_path)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)
file_handler.set_name('my_file_handler')
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)
console_handler.set_name('my_console_handler')
logger.addHandler(console_handler)


ts = time.time()
logger.info('=' * 65)
logger.info('Analysis started at {0}'.
            format(datetime.datetime.fromtimestamp(ts).
                   strftime('%Y%m%d %H:%M:%S')))
logger.info('Command line:\t{0}'.format(sys.argv[0]))
logger.info('Arguments:\t\t{0}'.format(' '.join(sys.argv[:])))
logger.info('=' * 65)

if args.write_sql:
    logger.info('Opened SQL connection: %s', db_location)


if not args.traffic_limit_pause_ms:
    # default pause after HTTP request: zero milliseconds
    args.traffic_limit_pause_ms = 0
else:
    args.traffic_limit_pause_ms = int(args.traffic_limit_pause_ms)
logger.info('Traffic Limit Pause (ms): %s' %
            str(args.traffic_limit_pause_ms))


if args.multiprocessing_cores:
    args.multiprocessing_cores = min(mp.cpu_count()-1,
                                     int(args.multiprocessing_cores))
else:
    args.multiprocessing_cores = 0


"""Create search_terms_regex, which stores the patterns that we
use for identifying sections in each of EDGAR documents types
"""
with open (path.join(project_dir, 'document_group_section_search.json'), 'r') as \
        f:
    json_text = f.read()
    search_terms = json.loads(json_text)
    if not search_terms:
        logger.error('Search terms file is missing or corrupted: ' +
              f.name)
search_terms_regex = copy(search_terms)
for filing in search_terms:
    for idx, section in enumerate(search_terms[filing]):
        for format in ['txt','html']:
            for idx2, pattern in enumerate(search_terms[filing][idx][format]):
                for startend in ['start','end']:
                    regex_string = search_terms[filing][idx][format] \
                        [idx2][startend]
                    regex_string = regex_string.replace('_','\\s{,5}')
                    regex_string = regex_string.replace('\n', '\\n')
                    search_terms_regex[filing][idx][format] \
                        [idx2][startend] = regex_string
"""identify which 'document' types are to be downloaded. If no command line
 argument given, then default to all of the document types listed in the
 JSON file"""
args.documents = args.documents or ','.join(list(search_terms.keys()))
args.documents = re.split(',', args.documents)          # ['10-K','10-Q']


def requests_get(url, params=None):
    """retrieve text via url, fatal error if no internet connection available
    :param url: source url
    :return: text retriieved
    """
    import requests, random
    retries = 0
    success = False
    hdr = {'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Mobile Safari/537.36'}
    while (not success) and (retries <= 20):
        # wait for an increasingly long time (up to a day) in case internet
        # connection is broken. Gives enough time to fix connection or SEC site
        try:
            # to test the timeout functionality, try loading this page:
            # http://httpstat.us/200?sleep=20000  (20 seconds delay before page loads)
            r = requests.get(url, headers=hdr, params=params, timeout=10)
            success = True
            # facility to add a pause to respect SEC EDGAR traffic limit
            # https://www.sec.gov/privacy.htm#security
            time.sleep(args.traffic_limit_pause_ms/1000)
        except requests.exceptions.RequestException as e:
            wait = (retries ^3) * 20 + random.randint(1,5)
            logger.warning(e)
            logger.info('URL: %s' % url)
            logger.info(
                'Waiting %s secs and re-trying...' % wait)
            time.sleep(wait)
            retries += 1
    if retries > 10:
        logger.error('Download repeatedly failed: %s',
                     url)
        sys.exit('Download repeatedly failed: %s' %
                 url)
    return r




