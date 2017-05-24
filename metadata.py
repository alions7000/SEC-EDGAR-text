"""
    secedgartext: extract text from SEC corporate filings
    Copyright (C) 2017  Alexander Ions

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import json
import re
import requests
from bs4 import BeautifulSoup, Tag, NavigableString

from utils import logger

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
        # self.date = ''
        # self.form_type_internal = ''
        self.document_group = ''
        self.section_name = ''
        self.endpoints = []
        self.extraction_method = ''
        self.warnings = []
        self.output_file = None
        self.time_elapsed = None

        if index_url:
            ri = requests.get(index_url)
            soup = BeautifulSoup(ri.text, 'html.parser')
            # Parse the page to find metadata
            index_metadata = {}
            form_type = soup.find('div', {'id': 'formHeader'}).\
                find_next('strong').string.strip()
            index_metadata['formHeader'] = form_type
            infoheads = soup.find_all('div', class_='infoHead')
            for i in infoheads:
                j = i.next_element
                while not (isinstance(j, Tag)) or not ('info') in \
                        j.attrs['class']:
                    j = j.next_element
                # remove colons, spaces, hyphens from dates/times
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

def load_from_json(file_path):
    metadata = Metadata()
    with open(file_path, 'r') as json_file:
        try:
            # data = json.loads(data_file.read().replace('\\', '\\\\'), strict=False)
            data = json.loads(json_file.read())
            metadata.sec_cik = data['sec_cik']
            metadata.sec_company_name = data['sec_company_name']
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
            # metadata.date = data['date']
            # metadata.form_type_internal = data['form_type_internal']
            metadata.document_group = data['form_group']
            metadata.section_name = data['section_name']
            metadata.endpoints = data['endpoints']
            metadata.extraction_method = data['extraction_method']
            metadata.warnings = data['warnings']
            metadata.output_file = data['output_file']
            metadata.time_elapsed = data['time_elapsed']
        except:
            logger.info('Could not load corrupted JSON file: ' + file_path)

    return metadata


