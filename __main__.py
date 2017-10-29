#!/usr/bin/env python3
"""
    secedgartext: extract text from SEC corporate filings
    Copyright (C) 2017  Alexander Ions

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from src.control import Downloader
from src.utils import logger, sql_cursor, sql_connection

def main():
    try:
        Downloader().download_companies(do_save_full_document=False)
    except Exception:
        # this makes sure that the full error message is recorded in
        # the logger text file for the process
        logger.exception("Fatal error in company downloading")

    # tidy up database before closing
    sql_cursor.execute("delete from metadata where sec_cik like 'dummy%'")
    sql_connection.close()


if __name__ == '__main__':
    main()








