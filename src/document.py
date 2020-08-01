"""
    secedgartext: extract text from SEC corporate filings
    Copyright (C) 2017  Alexander Ions

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import time
from datetime import datetime
import copy
import os
from abc import ABCMeta
import multiprocessing as mp

from .utils import search_terms as master_search_terms
from .utils import args, logger

class Document(object):
    __metaclass__ = ABCMeta

    def __init__(self, file_path, doc_text, extraction_method):
        self._file_path = file_path
        self.doc_text = doc_text
        self.extraction_method = extraction_method
        self.log_cache = []

    def get_excerpt(self, input_text, form_type, metadata_master,
                    skip_existing_excerpts):
        """

        :param input_text:
        :param form_type:
        :param metadata_master:
        :param skip_existing_excerpts:
        :return:
        """
        start_time = time.process_time()
        self.prepare_text()
        prep_time = time.process_time() - start_time
        file_name_root = metadata_master.metadata_file_name
        for section_search_terms in master_search_terms[form_type]:
            start_time = time.process_time()
            metadata = copy.copy(metadata_master)
            warnings = []
            section_name = section_search_terms['itemname']
            section_output_path = file_name_root + '_' + section_name
            txt_output_path = section_output_path + '_excerpt.txt'
            metadata_path = section_output_path + '_metadata.json'
            failure_metadata_output_path = section_output_path + '_failure.json'

            search_pairs = section_search_terms[self.search_terms_type()]
            text_extract, extraction_summary, start_text, end_text, warnings = \
                self.extract_section(search_pairs)
            time_elapsed = time.process_time() - start_time
            # metadata.extraction_method = self.extraction_method
            metadata.section_name = section_name
            if start_text:
                start_text = start_text.replace('\"', '\'')
            if end_text:
                end_text = end_text.replace('\"', '\'')
            metadata.endpoints = [start_text, end_text]
            metadata.warnings = warnings
            metadata.time_elapsed = round(prep_time + time_elapsed, 1)
            metadata.section_end_time = str(datetime.utcnow())
            if text_extract:
                # success: save the excerpt file
                metadata.section_n_characters = len(text_extract)
                with open(txt_output_path, 'w', encoding='utf-8',
                          newline='\n') as txt_output:
                    txt_output.write(text_extract)
                log_str = ': '.join(['SUCCESS Saved file for',
                                         section_name, txt_output_path])
                self.log_cache.append(('DEBUG', log_str))
                try:
                    os.remove(failure_metadata_output_path)
                except:
                    pass
                metadata.output_file = txt_output_path
                metadata.metadata_file_name = metadata_path
                metadata.save_to_json(metadata_path)
            else:
                log_str = ': '.join(['No excerpt located for ',
                                         section_name, metadata.sec_index_url])
                self.log_cache.append(('WARNING', log_str))
                try:
                    os.remove(metadata_path)
                except:
                    pass
                metadata.metadata_file_name = failure_metadata_output_path
                metadata.save_to_json(failure_metadata_output_path)
            if args.write_sql:
                metadata.save_to_db()
        return(self.log_cache)

    def prepare_text(self):
        # handled in child classes
        pass

