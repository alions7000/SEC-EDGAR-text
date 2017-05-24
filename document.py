"""
    secedgartext: extract text from SEC corporate filings
    Copyright (C) 2017  Alexander Ions

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import time
import copy
from abc import ABCMeta

from utils import search_terms as master_search_terms
from utils import logger

class Document(object):
    __metaclass__ = ABCMeta

    def __init__(self, file_path, doc_text):
        self._file_path = file_path
        self.doc_text = doc_text

    def get_excerpt(self, input_text, form_type, metadata_master,
                    skip_existing_excerpts):
        """

        :param input_text:
        :param form_type:
        :param metadata_master:
        :param skip_existing_excerpts:
        :return:
        """
        self.prepare_text()
        file_name_root = metadata_master.metadata_file_name
        for section_search_terms in master_search_terms[form_type]:
            # text_extract, start_text, end_text = None, None, None
            metadata = copy.copy(metadata_master)
            warnings = []
            section_name = section_search_terms['itemname']
            txt_output_path = file_name_root + '_' + section_name + '_excerpt.txt'
            metadata_path = file_name_root + '_' + section_name + '_metadata.json'
            metadata.metadata_file_name = metadata_path

            search_pairs = section_search_terms[self.document_type()]
            start_time = time.clock()

            text_extract, extraction_method, start_text, end_text, warnings = \
                self.extract_section(search_pairs)

            if warnings:
                logger.warning('Working with warnings for %s', self._file_path)
                for w in warnings:
                    print('\tWarning: ' + w)

            time_elapsed = time.clock() - start_time
            metadata.extraction_method = self.document_type()
            metadata.section_name = section_name
            if start_text:
                start_text = start_text.replace('\"', '\'')
            if end_text:
                end_text = end_text.replace('\"', '\'')
            metadata.endpoints = [start_text, end_text]
            metadata.warnings = warnings
            metadata.time_elapsed = round(time_elapsed, 1)
            if text_extract:
                # success: save the excerpt file
                with open(txt_output_path, 'w', encoding='utf-8') as txt_output:
                    txt_output.write(text_extract)
                logger.debug('SUCCESS: Saved excerpt file: %s', txt_output_path)
                metadata.output_file = txt_output_path
            metadata.save_to_json(metadata_path)

    def prepare_text(self):
        # handled in child classes
        pass

