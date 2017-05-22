"""
[License Boilerplate here: Alex copyright, license etc.]
"""

import logging
import os
import sys
import argparse
import re
from os import path
import datetime
import time
import json
from copy import copy


"""Parse the command line arguments
"""
companies_file_location = ''
single_company = ''
script_dir = path.dirname(__file__)
# / home / ai / projects_data / text_analysis / data - -company = DOW - -start = 20131231 - -end = 20141231
parser = argparse.ArgumentParser()
parser.add_argument('--storage')
parser.add_argument('--company')
parser.add_argument('--companies_list')
parser.add_argument('--filings')  #, default='10-K,10-Q'
parser.add_argument('--start')
parser.add_argument('--end')
args = parser.parse_args()
args.storage = args.storage or \
    path.join(script_dir, 'data')
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



"""Create search_terms_regex, which stores the patterns that we
use for identifying sections in the EDGAR documents
"""
with open (path.join(script_dir, 'document_group_section_regex.json'), 'r') as \
        f:
    json_text = f.read()
    search_terms = json.loads(json_text)
    search_terms_regex = copy(search_terms)
    for filing in search_terms:
        for idx, section in enumerate(search_terms[filing]):
            for format in ['txt','html']:
                for idx2, pattern in enumerate(search_terms[filing][idx][format]):
                    for startend in ['start','end']:
                        regex_string = search_terms[filing][idx][format] \
                            [idx2][startend]
                        regex_string = regex_string.replace('_','\\s')
                        regex_string = regex_string.replace('\n', '\\n')
                        search_terms_regex[filing][idx][format] \
                            [idx2][startend] = regex_string
