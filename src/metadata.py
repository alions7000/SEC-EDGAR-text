"""
    secedgartext: extract text from SEC corporate filings
    Copyright (C) 2017  Alexander Ions

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import json
import re
from bs4 import BeautifulSoup, Tag, NavigableString
import time
import random

from .utils import logger
from .utils import args, requests_get
from .utils import batch_number, batch_start_time, batch_machine_id
from .utils import sql_cursor, sql_connection


class Metadata(object):
    def __init__(self, index_url=None):
        self.sec_cik = ''
        self.sec_company_name = ''
        self.document_type = ''
        self.sec_form_header = ''
        self.sec_period_of_report = ''
        self.sec_filing_date = ''
        self.sec_changed_date = ''
        self.sec_accepted_date = ''
        self.sec_index_url = ''
        self.sec_url = ''
        self.metadata_file_name = ''
        self.original_file_name = ''
        self.original_file_size = ''
        self.document_group = ''
        self.section_name = ''
        self.section_n_characters = None
        self.endpoints = []
        self.extraction_method = ''
        self.warnings = []
        self.company_description = ''
        self.output_file = None
        self.time_elapsed = None
        self.batch_number = batch_number
        self.batch_signature = args.batch_signature or ''
        self.batch_start_time = str(batch_start_time)
        self.batch_machine_id = batch_machine_id
        self.section_end_time = None

        if index_url:
            index_metadata = {}
            attempts = 0
            while attempts < 5:
                try:
                    ri = requests_get(index_url)
                    logger.info('Status Code: ' + str(ri.status_code))
                    soup = BeautifulSoup(ri.text, 'html.parser')
                    # Parse the page to find metadata
                    form_type = soup.find('div', {'id': 'formHeader'}). \
                        find_next('strong').string.strip()
                    break
                except:
                    attempts += 1
                    logger.warning('No valid index page, attempt %i: %s'
                                   % (attempts, index_url))
                    time.sleep(attempts*10 + random.randint(1,5))

            index_metadata['formHeader'] = form_type
            infoheads = soup.find_all('div', class_='infoHead')
            for i in infoheads:
                j = i.next_element
                while not (isinstance(j, Tag)) or not ('info') in \
                        j.attrs['class']:
                    j = j.next_element
                # remove colons, spaces, hyphens from dates/times
                if type(j.string) is NavigableString:
                    index_metadata[i.string] = re.sub('[: -]', '',
                                                      j.string).strip()
            i = soup.find('span', class_='companyName')
            while not (isinstance(i, NavigableString)):
                i = i.next_element
            index_metadata['companyName'] = i.strip()
            i = soup.find(string='CIK')
            while not (isinstance(i, NavigableString)) or not (re.search('\d{10}', i.string)):
                i = i.next_element
            index_metadata['CIK'] = re.search('\d{5,}', i).group()

            for pair in [['Period of Report', 'sec_period_of_report'],
                         ['Filing Date', 'sec_filing_date'],
                         ['Filing Date Changed', 'sec_changed_date'],
                         ['Accepted', 'sec_accepted_date'],
                         ['formHeader', 'sec_form_header'],
                         ['companyName', 'sec_company_name'],
                         ['CIK', 'sec_cik']]:
                if pair[0] in index_metadata:
                    setattr(self, pair[1], index_metadata[pair[0]])

    def add_data_from_filing_text(self, text):
        """Scrape metadata from the filing document

        Find key metadata fields at the start of the filing submission,
        if they were not already found in the SEC index page
        :param text: full text of the filing
        """
        for pair in [['CONFORMED PERIOD OF REPORT:', 'sec_period_of_report'],
                     ['FILED AS OF DATE:', 'sec_filing_date'],
                     ['DATE AS OF CHANGE:', 'sec_changed_date'],
                     ['<ACCEPTANCE-DATETIME>', 'sec_accepted_date'],
                     ['COMPANY CONFORMED NAME:', 'sec_company_name'],
                     ['CENTRAL INDEX KEY::', 'sec_cik']]:
            srch = re.search('(?<=' + pair[0] + ').*', text)
            if srch and not getattr(self, pair[1]):
                setattr(self, pair[1], srch.group().strip())

    def save_to_json(self, file_path):
        """
        we effectively convert the Metadata object's data into a dict
        when we do json.dumps on it
        :param file_path:
        :return:
        """
        with open(file_path, 'w', encoding='utf-8') as json_output:
            # to write the backslashes in the JSON file legibly
            # (without duplicate backslashes), we have to
            # encode/decode using the 'unicode_escape' codec. This then
            # allows us to open the JSON file and click on the file link,
            # for immediate viewing in a browser.
            excerpt_as_json = json.dumps(self, default=lambda o: o.__dict__,
                                         sort_keys=False, indent=4)
            json_output.write(bytes(excerpt_as_json, "utf-8").
                              decode("unicode_escape"))


    def save_to_db(self):
        """Append metadata to sqlite database

        """

        # conn = sqlite3.connect(path.join(args.storage, 'metadata.sqlite3'))
        # c = conn.cursor()
        sql_insert = """INSERT INTO metadata (
            batch_number,
            batch_signature,
            batch_start_time,
            batch_machine_id,
            sec_cik,
            company_description,
            sec_company_name,
            sec_form_header,
            sec_period_of_report,
            sec_filing_date,
            sec_index_url,
            sec_url,
            metadata_file_name,
            document_group,
            section_name,
            section_n_characters,
            section_end_time,
            extraction_method,
            output_file,
            start_line,
            end_line,
            time_elapsed) VALUES
            """ + "('" + "', '".join([str(self.batch_number),
                       str(self.batch_signature),
                       str(self.batch_start_time)[:-3],  # take only 3dp microseconds
                       self.batch_machine_id,
                       self.sec_cik,
                       re.sub("[\'\"]","", self.company_description).strip(),
                       re.sub("[\'\"]","", self.sec_company_name).strip(),
                       self.sec_form_header, self.sec_period_of_report,
                       self.sec_filing_date,
                       self.sec_index_url, self.sec_url,
                       self.metadata_file_name, self.document_group,
                       self.section_name, str(self.section_n_characters),
                       str(self.section_end_time)[:-3],
                       self.extraction_method,
                       str(self.output_file),
                       re.sub("[\'\"]","", self.endpoints[0]).strip()[0:200],
                       re.sub("[\'\"]","", self.endpoints[1]).strip()[0:200],
                       str(self.time_elapsed)]) + "')"
        sql_insert = sql_insert.replace("'None'","NULL")
        sql_cursor.execute(sql_insert)
        sql_connection.commit()


def load_from_json(file_path):
    metadata = Metadata()
    with open(file_path, 'r') as json_file:
        try:
            # data = json.loads(data_file.read().replace('\\', '\\\\'), strict=False)
            data = json.loads(json_file.read())
            metadata.sec_cik = data['sec_cik']
            metadata.sec_company_name = data['sec_company_name']
            metadata.company_description = data['company_description']
            metadata.document_type = data['document_type']
            metadata.sec_form_header = data['sec_form_header']
            metadata.sec_period_of_report = data['sec_period_of_report']
            metadata.sec_filing_date = data['sec_filing_date']
            metadata.sec_changed_date = data['sec_changed_date']
            metadata.sec_accepted_date = data['sec_accepted_date']
            metadata.sec_accepted_date = data['sec_accepted_date']
            metadata.sec_url = data['sec_url']
            metadata.metadata_file_name = data['metadata_file_name']
            metadata.original_file_name = data['original_file_name']
            metadata.original_file_size = data['original_file_size']
            metadata.document_group = data['form_group']
            metadata.section_name = data['section_name']
            metadata.section_n_characters = data['section_n_characters']
            metadata.endpoints = data['endpoints']
            metadata.extraction_method = data['extraction_method']
            metadata.warnings = data['warnings']
            metadata.output_file = data['output_file']
            metadata.time_elapsed = data['time_elapsed']
            metadata.batch_number = data['batch_number']
            metadata.batch_signature = data['batch_signature']
            metadata.batch_start_time = data['batch_start_time']
            metadata.batch_machine_id = data['batch_machine_id']
            metadata.section_end_time = data['section_end_time']

        except:
            logger.info('Could not load corrupted JSON file: ' + file_path)

    return metadata

