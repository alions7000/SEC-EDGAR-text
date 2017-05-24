"""
    secedgartext: extract text from SEC corporate filings
    Copyright (C) 2017  Alexander Ions

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
# Originally adapted from "SEC-Edgar" package code
import os
import re
import copy
import requests
from bs4 import BeautifulSoup

from utils import logger
from metadata import Metadata
from utils import search_terms as master_search_terms
from html_document import HtmlDocument
from text_document import TextDocument


class EdgarCrawler(object):
    def __init__(self, storage_folder):
        self.storage_folder = storage_folder

    def download_filings(self, company_description, edgar_search_string,
                         filing_search_string,
                         start_date, end_date,
                         do_save_full_document, count=9999):
        """Build a list of all filings of a certain type, within a date range.

        Then download them and extract the text of interest
        :param: cik
        :param: count number of Filing Results to return on the (first) EDGAR
            Search Results query page. 9999=show all
        :param: type_serach_string
        :param: start_date, end_date
        :return: text_extract: str , warnings: [str]
        """

        filings_links = self.download_filings_links(edgar_search_string,
                                                    company_description,
                                                    filing_search_string,
                                                    start_date, end_date, count)

        filings_list = []

        logger.info("Identified " + str(len(filings_links)) +
                    " filings, gathering SEC metadata and document links...")
        for k in filings_links:
            # Get the URL for the (text-format) document which packages all
            # of the parts of the filing
            URLbase = re.sub('-index.htm.?','',k)
            filing_url = URLbase + ".txt"
            doc_description = str(company_description).strip()
            filings_list.append([k, filing_url, doc_description])

        if filings_links:
            for i, filing_info in enumerate(filings_list):
                logger.info("Downloading filing %i / %i from %s", i + 1,
                            len(filings_list), filing_info[2])
                self.download_filing(filing_info, do_save_full_document)
            logger.debug("Finished attempting to download all the %s forms for %s",
                         filing_search_string, company_description)
        else:
            logger.warning("No filings found")



    def download_filings_links(self, edgar_search_string, company_description,
                               filing_search_string,
                               start_date, end_date, count):
        """[docstring here]
        :param edgar_search_string: 10-digit integer CIK code, or ticker
        :param company_description:
        :param filing_search_string: e.g. '10-K'
        :param start_date: ccyymmdd
        :param end_date: ccyymmdd
        :param count:
        :return: linkList, a list of links to main pages for each filing found
        example of a typical base_url: http://www.sec.gov/cgi-bin/browse-secedgartext?action=getcompany&CIK=0000051143&type=10-K&datea=20011231&dateb=20131231&owner=exclude&output=xml&count=9999
        """
        base_url = "http://www.sec.gov/cgi-bin/browse-edgar" + \
                   "?action=getcompany&CIK=" + \
                   str(edgar_search_string) + "&type=" + \
                   filing_search_string + "&datea=" + \
                   str(start_date) + "&dateb=" + str(end_date) + \
                   "&owner=exclude&output=xml&count=" + str(count)
        logger.info('-' * 100)
        logger.info(
            "Query EDGAR database for " + filing_search_string + ", Search: " +
            str(edgar_search_string) + " (" + company_description + ")")
        logger.debug("URL: " + base_url)
        logger.info('-' * 100)
        r = requests.get(base_url)
        data = r.text
        soup = BeautifulSoup(data, "html.parser")

        linkList = []  # List of all links from the CIK page
        for link in soup.find_all('filinghref'):
            URL = link.string
            linkList.append(URL)
        return linkList


    def download_filing(self, filing_info, do_save_full_document):
        """
        Download filing, extract relevant sections.

        Download a filing (full filing submission). Find relevant <DOCUMENT>
        portions of the filing, and send the raw text for text extraction
        :param: doc_info: contains URL for the full filing submission, and
        other EDGAR index metadata
        """

        index_url = filing_info[0]
        base_url = filing_info[1]
        filing_metadata = Metadata(index_url)
        logger.debug("URL: " + base_url)
        logger.info("filing: %s, %s, period: %s",
                    filing_metadata.sec_company_name,
                    filing_metadata.sec_form_header,
                    filing_metadata.sec_period_of_report)
        filing_metadata.sec_index_url = index_url
        filing_metadata.sec_url = base_url
        try:
            r = requests.get(base_url)
            filing_text = r.text
        except:
            r = None
            filing_text = ''
            logger.warning('EdgarCrawler: Failed to download file %s',
                           base_url)
            logger.warning('(%s, %s, %s)', filing_info[2],
                           filing_metadata.sec_form_header,
                           filing_metadata.sec_company_name)
        filing_metadata.add_data_from_filing_text(filing_text[0:10000])

        # Iterate through the DOCUMENT types that we are seeking,
        # checking for each in turn whether they are included in the current
        # filing. Note that searching for document_group '10-K' will also
        # deliberately find DOCUMENT type variants such as 10-K/A, 10-K405 etc.
        # Note we search for all DOCUMENT types that interest us, regardless of
        # whether the current filing came from a '10-K' or '10-Q' web query
        # originally. Also note that we process DOCUMENT types in no
        # fixed order.
        for document_group in master_search_terms:
            doc_search = re.search("<DOCUMENT>.{,20}<TYPE>" + document_group +
                                   ".*</DOCUMENT>", filing_text,
                                   flags=re.DOTALL | re.IGNORECASE)
            if doc_search:
                doc_text = doc_search.group()
                doc_metadata = copy.copy(filing_metadata)
                # look for form type near the start of the document.
                type_search = re.search("(?i)<TYPE>.*",
                                        doc_text[0:10000])
                if type_search:
                    document_type = re.sub("^(?i)<TYPE>", "", type_search.group())
                    document_type = re.sub(r"(-|/|\.)", "",
                                         document_type)  # remove hyphens etc
                else:
                    document_type = "document_TYPE_not_tagged"
                    logger.error("form <TYPE> not given in form?: " + base_url)

                local_path = os.path.join(self.storage_folder,
                        "/" + filing_info[2] + '_' + \
                        filing_metadata.sec_cik + "_" + document_type + "_" + \
                        filing_metadata.sec_period_of_report)
                doc_metadata.document_type = document_type
                # doc_metadata.form_type_internal = form_string
                doc_metadata.document_group = document_group
                doc_metadata.metadata_file_name = local_path

                # search for a <html>...</html> block in the DOCUMENT
                html_search = re.search(r"<(?i)html>.*?</(?i)html>",
                                        doc_text, re.DOTALL)
                # occasionally a (somewhat corrupted) filing includes a mixture
                # of HTML-format documents, but some of them are enclosed in
                # <TEXT>...</TEXT> tags and others in <HTML>...</HTML> tags.
                # If the first <TEXT>-enclosed document is before the first
                # <HTML> enclosed one, then we take that one instead of
                # the block identified in html_search.
                text_search = re.search(r"<(?i)text>.*?</(?i)text>",
                                        doc_text, re.DOTALL)
                if text_search and html_search \
                        and text_search.start() < html_search.start() \
                        and html_search.start() > 5000:
                    html_search = text_search
                if html_search:
                    # if there's an html block inside the DOCUMENT then just
                    # take this instead of the full DOCUMENT text
                    doc_text = html_search.group()
                    main_path = local_path + ".htm"
                else:
                    main_path = local_path + ".txt"
                doc_metadata.original_file_size = str(len(doc_text)) + ' chars'
                if html_search:
                    reader_class = HtmlDocument
                else:
                    reader_class = TextDocument
                logger.debug('Attempting to extract sections using: %s',
                             doc_metadata.metadata_file_name)
                reader_class(doc_metadata.original_file_name,
                             doc_text).get_excerpt(doc_text, document_group,
                                                   doc_metadata,
                                                   skip_existing_excerpts=False)
                if do_save_full_document:
                    with open(main_path, "w") as filename:
                        filename.write(doc_text)
                    logger.debug(
                        "Saved file: " + main_path + ', ' +
                        str(round(os.path.getsize(main_path) / 1024)) + ' KB')
                    filing_metadata.original_file_name = main_path
                else:
                    filing_metadata.original_file_name = \
                        "file was not saved locally"


