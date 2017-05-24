# SEC EDGAR Text
Download company filings from the SEC EDGAR service, and find key text
sections of interest.

Download key text sections of SEC EDGAR company filings. Format, organise
and store the text excerpts ready for both automated processing (NLP) and
for human reading (spot-checking). Structured storage of text and
metadata, with logging of failed document analyses. Suitable for
automation of large-scale downloads, with flexibility to customise
which sections of the documents are extracted. Compatible with all
main EDGAR document formats from 1993 onwards.

Generally accurate in extracting text, but lots of room for improvement.
Comments and contributions welcome!



#### About the project

* I used [SEC-Edgar-Crawler](https://github.com/rahulrrixe/sec-edgar)
for initial ideas which helped this project.
* Thanks to my colleagues at Rosenberg Equities for help with an earlier
attempt to download EDGAR data.

## Installation


## Usage
Typical usage (default: download the 500 companies in 'companies_list.txt'):

```python secedgartext --storage=/tmp/storage_folder```


## Background
### About EDGAR

*History and future of EDGAR, links to key SEC procedures documents etc.*



### Retrieving text data from EDGAR

*Screenshots, picutres of EDGAR documents here*


### Other packages
Many specialised projects automate access to EDGAR filings.
Some access text data, like this one. Most focus on downloading whole
filing documents, financial statements information, or parsing
XBRL filings. This package aims to make access to large volumes of text
information easier and more consistent.