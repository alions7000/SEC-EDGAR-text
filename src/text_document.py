"""
    secedgartext: extract text from SEC corporate filings
    Copyright (C) 2017  Alexander Ions

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import re

from .document import Document


class TextDocument(Document):
    def __init__(self, *args, **kwargs):
        super(TextDocument, self).__init__(*args, **kwargs)

    def search_terms_type(self):
        return "txt"

    def extract_section(self, search_pairs):
        """

        :param search_pairs:
        :return:
        """
        start_text = 'na'
        end_text = 'na'
        warnings = []
        text_extract = None
        for st_idx, st in enumerate(search_pairs):
            # ungreedy search (note '.*?' regex expression between 'start' and 'end' patterns
            # also using (?:abc|def) for a non-capturing group
            # st = super().search_terms_pattern_to_regex()
            # st = Reader.search_terms_pattern_to_regex(st)
            item_search = re.findall(st['start'] + '.*?' + st['end'],
                                     self.doc_text,
                                     re.DOTALL | re.IGNORECASE)
            if item_search:
                longest_text_length = 0
                for s in item_search:
                    text_extract = s.strip()
                    if len(s) > longest_text_length:
                        longest_text_length = len(text_extract)
                # final_text_new = re.sub('^\n*', '', final_text_new)
                final_text_lines = text_extract.split('\n')
                start_text = final_text_lines[0]
                end_text = final_text_lines[-1]
                break
        if text_extract:
            # final_text = '\n'.join(final_text_lines)
            # text_extract = remove_table_lines(final_text)
            text_extract = remove_table_lines(text_extract)
            extraction_summary = self.extraction_method + '_document'
        else:
            warnings.append('Extraction did not work for text file')
            extraction_summary = self.extraction_method + '_document: failed'
        return text_extract, extraction_summary, start_text, end_text, warnings

def remove_table_lines(input_text):
    """Replace lines believed to be part of numeric tables with a placeholder.

    :param input_text:
    :return:
    """
    text_lines = []
    table_lines = []
    post_table_lines = []
    is_in_a_table = False
    is_in_a_post_table = False
    all_lines = input_text.splitlines(True)
    for i, line in enumerate(all_lines, 0):
        if is_table_line(line):
            # a table line, possibly not part of an excerpt
            if is_in_a_post_table:
                # table resumes: put the inter-table lines into the table_line list
                table_lines = table_lines + post_table_lines
                post_table_lines = []
                is_in_a_post_table = False
            table_lines.append(line)
            is_in_a_table = True
        else:
            # not a table line
            if is_in_a_table:
                # the first post-table line
                is_in_a_table = False
                is_in_a_post_table = True
                post_table_lines.append(line)
            elif is_in_a_post_table:
                # 2nd and subsequent post-table lines, or final line
                if len(post_table_lines) >= 4:
                    # sufficient post-table lines have accumulated now that we
                    # revert to standard 'not a post table' mode.
                    # We append the post-table lines to the text_lines,
                    # and we discard the table_lines
                    if len(table_lines) >= 3:
                        text_lines.append(
                            '[DATA_TABLE_REMOVED_' +
                            str(len(table_lines)) + '_LINES]\n\n')
                    else:
                        # very short table, so we just leave it in
                        # the document regardless
                        text_lines = text_lines + table_lines
                    text_lines = text_lines + post_table_lines
                    table_lines = []
                    post_table_lines = []
                    is_in_a_post_table = False
                else:
                    post_table_lines.append(line)
        if not (is_in_a_table) and not (is_in_a_post_table):
            # normal excerpt line: just append it to text_lines
            text_lines.append(line)
    # Tidy up any outstanding table_lines and post_table_lines at the end
    if len(table_lines) >= 3:
        text_lines.append(
            '[DATA_TABLE_REMOVED_' + str(len(table_lines)) + '_LINES]\n\n')
    else:
        text_lines = text_lines + table_lines
    text_lines = text_lines + post_table_lines

    final_text = ''.join(text_lines)
    return final_text


def is_table_line(s):
    """Is text line string s likely to be part of a numeric table?

    gaps between table 'cells' are expected to have three or more whitespaces,
    and table rows are expected to have at least 3 such gaps, i.e. 4 columns

    :param s:
    :return:
    """
    s = s.replace('\t', '    ')
    rs = re.findall('\S\s{3,}', s)  # \S = non-whitespace, \s = whitespace
    r = re.search('(<TABLE>|(-|=|_){5,})', s)  # check for TABLE quasi-HTML tag,
    # or use of lots of punctuation marks as table gridlines
    # Previously also looking for ^\s{10,}[a-zA-z] "lots of spaces prior to
    # the first (non-numeric i.e. not just a page number marker) character".
    # Not using this approach because risk of confusion with centre-justified
    # section headings in certain text documents
    return len(rs) >= 2 or r != None