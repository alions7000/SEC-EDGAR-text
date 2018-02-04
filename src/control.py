"""
    secedgartext: extract text from SEC corporate filings
    Copyright (C) 2017  Alexander Ions

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import re
import os

from .download import EdgarCrawler
from .utils import logger, args
from .utils import companies_file_location, single_company, date_search_string
from .utils import batch_number, storage_toplevel_directory

MAX_FILES_IN_SUBDIRECTORY = 1000

class Downloader(object):
    def __init__(self):
        self.storage_path = args.storage

    def download_companies (self, do_save_full_document=False):
        """Iterate through a list of companies and download documents.

        Downloading document contents within each filing type required
        :param do_save_full_document: save a local copy of the whole original
        document
        :return:
        """
        companies = list()
        if single_company:
            companies.append([str(single_company), str(single_company)])
            logger.info("Downloading single company: %s", args.company)
        if not companies:
            try:
                companies = company_list(companies_file_location)
                logger.info("Using companies list: %s",
                            companies_file_location)
            except:
                logger.warning("Companies list not available")
                company_input = input("Enter company code (CIK or ticker): ")
                if company_input:
                    companies.append([company_input, company_input])
                    logger.info("Downloading single company: %s", company_input)
                else:
                    # default company: Dow Chemical
                    company_default = 'DOW'
                    companies.append([company_default, company_default.title()])
                    logger.info("Downloading default company: %s",
                                next(iter(companies)))
        start_date =  args.start    # TODO:this may be ignored by EDGAR web interface, consider removing this argument
        end_date = args.end
        filings = args.filings

        logger.info('-' * 65)
        logger.info("Downloading %i companies: %s", len(companies),
                    single_company or companies_file_location)
        logger.info("Filings period: %i - %i", args.start, args.end)
        logger.info("Filings search: %s", filings)
        logger.info("Storage location: %s", self.storage_path)
        logger.info('-' * 65)

        start_company = max(1, int(args.start_company or 1))
        end_company = min(len(companies),
                          int(args.end_company or len(companies)))

        download_companies = companies[start_company-1:end_company]
        seccrawler = EdgarCrawler()


        if do_save_full_document:
            logger.info("Saving source document and extracts "
                        "(if successful) locally")
        else:
            logger.info("Saving extracts (if successful) only. "
                        "Not saving source documents locally.")
        logger.info("SEC filing date range: %i to %i", start_date, end_date)
        storage_subdirectory_number = 1

        for c, company_keys in enumerate(download_companies):
            edgar_search_string = str(company_keys[0])
            company_description = str(company_keys[1]).strip()
            company_description = re.sub('/','', company_description)

            logger.info('Batch number: ' + str(batch_number) +
                        ', begin downloading company: ' +
                        str(c + 1) + ' / ' +
                        str(len(download_companies)))
            storage_subdirectory = os.path.join(storage_toplevel_directory,
                                               format(storage_subdirectory_number,
                                                      '03d'))
            if not os.path.exists(storage_subdirectory):
                os.makedirs(storage_subdirectory)
            seccrawler.storage_folder = storage_subdirectory
            for filing_search_string in args.filings:
                seccrawler.download_filings(company_description,
                                            edgar_search_string,
                                            filing_search_string,
                                            date_search_string,
                                            str(start_date),
                                            str(end_date), do_save_full_document)
            if len(os.listdir(storage_subdirectory)) > MAX_FILES_IN_SUBDIRECTORY:
                storage_subdirectory_number += 1
        logger.warning("SUCCESS: Finished attempted download of " +
                       str(len(download_companies) or 0) +
                       " companies from an overall list of " +
                       str(len(companies) or 0) + " companies." )


def company_list(text_file_location):
    """Read companies list from text_file_location, load into a dictionary.
    :param text_file_location:
    :return: company_dict: each element is a list of CIK code text and
    company descriptive text
    """
    company_list = list()
    with open(text_file_location, newline='') as f:
        for r in f.readlines():
            if r[0] =='#' and len(company_list) > 0:
                break
            if r[0] != '#' and len(r) > 1:
                r = re.sub('\n', '', r)
                text_items = re.split('[ ,\t]', r)  # various delimiters allowed
                edgar_search_text = text_items[0].zfill(10)
                company_description = '_'.join(
                    text_items[1:2])
                company_list.append([edgar_search_text, company_description])
    return company_list



