import sys
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTChar, LTFigure
from PyPDF2 import PdfFileReader
import json
import unidecode
import unicodedata
import re
import os
sys.path.append(str(os.getcwd()))
from fuzzywuzzy import fuzz
import csv
import codecs

class PdfMinerWrapper(object):
    def __init__(self, pdf_doc, pdf_pwd=""):
        self.pdf_doc = pdf_doc
        self.pdf_pwd = pdf_pwd

    def __enter__(self):
        # open the pdf file
        self.fp = open(self.pdf_doc, 'rb')
        # create a parser object associated with the file object
        parser = PDFParser(self.fp)
        # create a PDFDocument object that stores the document structure
        doc = PDFDocument(parser, password=self.pdf_pwd)
        # connect the parser and document objects
        parser.set_document(doc)
        self.doc = doc
        return self

    def _parse_pages(self):
        rsrcmgr = PDFResourceManager()
        laparams = LAParams(char_margin=3.5, all_texts=True)
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        for page in PDFPage.create_pages(self.doc):
            interpreter.process_page(page)
            # receive the LTPage object for this page
            layout = device.get_result()
            # layout is an LTPage object which may contain child objects like LTTextBox, LTFigure, LTImage, etc.
            yield layout

    def __iter__(self):
        return iter(self._parse_pages())

    def __exit__(self, _type, value, traceback):
        self.fp.close()


def get_page_obj():
    obj = dict()
    obj['text'] = ''
    obj['bbox'] = ''
    obj['spans'] = {'font_name': '', 'font_size': '', 'bbox': '', 'text': ''}
    return obj


def calculate_bbox(page_height, bbox):
    new_bbox = [bbox[0], 0, bbox[2], 0]
    new_bbox[1] = page_height - bbox[3]
    new_bbox[3] = page_height - bbox[1]


def extract_attributes(path, toc):
    result = dict()
    fontdict = dict()
    final_result = []

    with PdfMinerWrapper(path) as doc:
        for page in doc:
            result[page.pageid - 1] = []
            fontsize = None
            fontname = None
            for tbox in page:
                if not isinstance(tbox, LTTextBox):
                    continue
                for obj in tbox:
                    
                    for c in obj:
                        if not isinstance(c, LTChar):
                            continue
                        fontname = c.fontname
                        fontsize = c.size
                    if fontname in fontdict:
                        val = fontdict[fontname]
                        fontdict[fontname] = val + 1
                    else:
                        fontdict[fontname] = 1
        max_font_count = 0
        max_font = None
        for key in fontdict:
            if fontdict[key] > max_font_count:
                max_font_count = fontdict[key]
                max_font = key

        for page in doc:
            is_section_start_temp = False
            result[page.pageid - 1] = []
            fontsize = None
            fontname = None
            for tbox in page:
                if not isinstance(tbox, LTTextBox):
                    continue
                for obj in tbox:
                    is_section_start = False
                    possible_heading = False
                    prev_fontname = None
                    all_same_font = True
                    for c in obj:
                        if not isinstance(c, LTChar):
                            continue
                        fontname = c.fontname
                        if prev_fontname is not None and prev_fontname != fontname:
                            all_same_font = False
                        prev_fontname = fontname
                        fontsize = c.size
#                    if fontname != max_font and all_same_font:
#                        possible_heading = True
                    if all_same_font:
                        possible_heading = True
                    if compare_text_with_top_level_headings(obj.get_text(), toc):
                        is_section_start = True
                        fontname = None
                        fontsize = None
                        obj.bbox = None
                        possible_heading = None
                    if (not is_section_start_temp) or clean_string(obj.get_text().strip()) != clean_string(page_section_map[int(page.pageid - 1)].strip()):
                       final_result_element = (obj.get_text().strip(), fontname, fontsize, obj.bbox, possible_heading, is_section_start, page.pageid, page.height, page.width)
                       final_result.append(final_result_element)
    return final_result

def compare_text_with_top_level_headings(text, toc):
    for element in toc:
        toc_text = element[0]
        toc_text_level = element[2]
        if (text.strip() == toc_text.strip() or fuzz.ratio(text, toc_text) > 90) and toc_text_level == 1:
            return True
    return False

#def get_level_heading_page_map(toc_pypdf2):

def flatten_toc(toc_pypdf2, flattened_toc, level, reader):
    if isinstance(toc_pypdf2, list):
        for element in toc_pypdf2:
            flattened_toc = flatten_toc(element, flattened_toc, level + 1, reader)
    else:
            toc_pypdf2_str = str(toc_pypdf2)
            start = "'/Page': IndirectObject("
            end = ", 0)"
            toc_pypdf2_page = (toc_pypdf2_str.split(start))[1].split(end)[0]
            flattened_toc.append((clean_string(toc_pypdf2['/Title']), reader._getPageNumberByIndirect(int(toc_pypdf2_page)), level))
    return flattened_toc

def get_table_of_contents(filename):
    reader = PdfFileReader(open(filename, 'rb'))
    toc_pypdf2 = reader.outlines
    flattened_toc = []
    flattened_toc = flatten_toc(toc_pypdf2, flattened_toc, 0, reader)
    flattened_toc = clean_extracted_toc(flattened_toc)
    return flattened_toc

def clean_extracted_toc(toc):
    new_toc = []
    for element in toc:
        (text, page_no, level) = element
        cleaned_text = clean_string(text)
        cleaned_text = cleaned_text.replace('"', "'")
        new_toc.append((cleaned_text, page_no, level))
    return new_toc

def clean_extracted_pdf(pdf_attributes):
    new_pdf_attributes = []
    for line in pdf_attributes:
        (text, fontname, fontsize, bbox, possible_heading, is_section_start, page_no, page_height, page_width) = line
        cleaned_text = clean_string(text)
        cleaned_text = cleaned_text.replace('"', "'")
        new_pdf_attributes.append((cleaned_text, fontname, fontsize, bbox, possible_heading, is_section_start, page_no, page_height, page_width))
    return new_pdf_attributes
    

def char_filter(string):
    latin = re.compile('[a-zA-Z]+')
    for char in unicodedata.normalize('NFC', string):
        decoded = unidecode.unidecode(char)
        if latin.match(decoded):
            yield char
        else:
            yield decoded

def clean_string(string):
    return "".join(char_filter(string))


pdf_attributes = extract_attributes(sys.argv[1],[])
pdf_attributes = clean_extracted_pdf(pdf_attributes)
with open('pdf_attributes.csv', 'w') as f:
    writer = csv.writer(f)
    all_rows = []
#    first_row = ['page_no','line','is_heading','is_paragraph_end','pdf_attribute']
    first_row  =['page_no','line','is_paragraph_end','is_heading','is_header','is_footer','is_bullet_head','is_bullet_body','is_image_caption','is_table_caption','is_table_content','is_toc','is_toc_heading','is_page_no','is_doc_title','pdf_attribute']
    all_rows.append(first_row)
    for attr in pdf_attributes:
        row = []
        text = attr[0]
        row.append(str(attr[-3]))
        row.append(text)
        for k in range(0,len(first_row) - 3):
            row.append(0)
        row.append(str(attr))
        all_rows.append(row)
    writer.writerows(all_rows)
