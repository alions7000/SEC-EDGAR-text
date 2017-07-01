"""
    secedgartext: extract text from SEC corporate filings
    Copyright (C) 2017  Alexander Ions

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import logging
import os
import sys
import argparse
import re
from os import path
import socket
import time
import datetime
import json
import sqlite3
from copy import copy


"""Parse the command line arguments
"""
companies_file_location = ''
single_company = ''
script_dir = path.dirname(__file__)
parser = argparse.ArgumentParser()
parser.add_argument('--storage')
parser.add_argument('--write_sql')
parser.add_argument('--company')
parser.add_argument('--companies_list')
parser.add_argument('--filings')
parser.add_argument('--documents')
parser.add_argument('--start')
parser.add_argument('--end')
parser.add_argument('--report_period')
parser.add_argument('--batch_signature')
parser.add_argument('--start_company')
parser.add_argument('--end_company')
args = parser.parse_args()
args.storage = args.storage or \
    path.join(script_dir, 'data')
args.write_sql = args.write_sql or True
if args.company:
    single_company = args.company
else:
    if args.companies_list:
        companies_file_location = os.path.join(script_dir, args.companies_list)
    else:
        companies_file_location = os.path.join(script_dir, 'companies_list.txt')


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



"""Set up logging
"""
# log_file_name = 'sec_extractor_{0}.log'.format(ts)
log_file_name = 'sec_edgar_text.log'
log_path = path.join(args.storage, log_file_name)

logger = logging.getLogger('text_analysis')
# # set up the logger if it hasn't already been set up earlier in the execution run
# if not(logger.hasHandlers()):
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


"""Set up the metadata database
"""
if args.write_sql:
    db_location = path.join(args.storage, 'metadata.sqlite3')
    conn = sqlite3.connect(db_location)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS metadata (
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
    conn.commit()
    c.execute('SELECT max(batch_number) FROM metadata')
    query_result =c.fetchone()
    if query_result and query_result[0]:
        batch_number = query_result[0] + 1
    else:
        batch_number = 1
    conn.close()
    batch_start_time = datetime.datetime.utcnow()
    batch_machine_id = socket.gethostname()
    logger.info("Writing metadata to JSON files and to database: %s"
                % db_location)
else:
    logger.warning("Writing metadata to JSON files, not to database")



"""Create search_terms_regex, which stores the patterns that we
use for identifying sections in each of EDGAR documents types
"""
with open (path.join(script_dir, 'document_group_section_search.json'), 'r') as \
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


def requests_get(url):
    """retrieve text via url, fatal error if no internet connection available
    :param url: source url
    :return: text retriieved
    """
    import requests
    retries = 0
    success = False
    while (not success) and (retries <= 10):
        try:
            r = requests.get(url)
            success = True
        except Exception as e:
            wait = retries * 10
            logger.warning(
                'Download Error! Waiting %s secs and re-trying...' % wait)
            time.sleep(wait)
            retries += 1
    if retries > 10:
        logger.error('No internet connection available: %s',
                     url)
        sys.exit('No internet connection available: %s' %
                 url)
    return r



