import sys
from pdfminer3.pdfparser import PDFParser
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfdocument import PDFDocument
from pdfminer3.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer3.converter import PDFPageAggregator
from pdfminer3.layout import LAParams, LTTextBox, LTChar, LTFigure
from PyPDF2 import PdfFileReader
import pdfrw
from collections import defaultdict
import json
import unidecode
import unicodedata
import re
import os
from string import printable

sys.path.append(str(os.getcwd()))
from fuzzywuzzy import fuzz
import csv
import codecs

pdf_name = ''
all_word_coords = defaultdict(dict)


class PdfMinerWrapper(object):
    def __init__(self, pdf_doc, pdf_pwd=""):
        self.pdf_doc = pdf_doc
        self.pdf_pwd = pdf_pwd
        global pdf_name
        pdf_name = self.pdf_doc

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

    def get_pdf(self):
        print('in get pdf')
        return self.pdf_doc


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
    global all_words_coords

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
                        if not isinstance(c, LTChar) :
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
                    letter_list = []
                    word = ''
                    is_section_start = False
                    possible_heading = False
                    prev_fontname = None
                    all_same_font = True

                    text = clean_string(obj.get_text().strip())
                    text = text.replace('"', "'")
                    for c in obj:
                        if not (c.get_text() == ' ' or c.get_text()=='\n'):
                            letter_list.append(c)
                            word += c.get_text()
                        else:
                            if letter_list :
                                all_word_coords[text].update(
                                    { (int(letter_list[0].x0), int(letter_list[-1].x1)):word})

                            letter_list = []
                            word = ''
                        if isinstance(c,LTChar):
                            fontname = c.fontname
                            fontsize = c.size
                        if prev_fontname is not None and prev_fontname != fontname:
                            all_same_font = False
                        prev_fontname = fontname


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
                    if obj.get_text().strip()!='' and ((not is_section_start_temp) or clean_string(obj.get_text().strip()) != clean_string(
                            page_section_map[int(page.pageid - 1)].strip())):
                        final_result_element = (
                        obj.get_text().strip(), fontname, fontsize, obj.bbox, possible_heading, is_section_start,
                        page.pageid, page.height, page.width)
                        final_result.append(final_result_element)
    return final_result


def compare_text_with_top_level_headings(text, toc):
    for element in toc:
        toc_text = element[0]
        toc_text_level = element[2]
        if (text.strip() == toc_text.strip() or fuzz.ratio(text, toc_text) > 90) and toc_text_level == 1:
            return True
    return False


# def get_level_heading_page_map(toc_pypdf2):

def flatten_toc(toc_pypdf2, flattened_toc, level, reader):
    if isinstance(toc_pypdf2, list):
        for element in toc_pypdf2:
            flattened_toc = flatten_toc(element, flattened_toc, level + 1, reader)
    else:
        toc_pypdf2_str = str(toc_pypdf2)
        start = "'/Page': IndirectObject("
        end = ", 0)"
        toc_pypdf2_page = (toc_pypdf2_str.split(start))[1].split(end)[0]
        flattened_toc.append(
            (clean_string(toc_pypdf2['/Title']), reader._getPageNumberByIndirect(int(toc_pypdf2_page)), level))
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
        new_pdf_attributes.append((cleaned_text, fontname, fontsize, bbox, possible_heading, is_section_start, page_no,
                                   page_height, page_width, []))
    new_pdf_attributes = extract_hyperlinks(new_pdf_attributes)
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


def get_pdf_attributes(file_path):
    pdf_attributes = extract_attributes(file_path, [])
    pdf_attributes = clean_extracted_pdf(pdf_attributes)
    pdf_attributes = [[attr[6], 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, attr] for attr in pdf_attributes]
    return pdf_attributes
# pdf_attributes = get_pdf_attributes(sys.argv[1])
# print(pdf_attributes)

def generate_pdf_attributes_csv():
    count = 0
    pdf_attributes = get_pdf_attributes(sys.argv[1])
    with open('pdf_attributes.csv', 'w') as f:
        writer = csv.writer(f)
        all_rows = []
        #    first_row = ['page_no','line','is_heading','is_paragraph_end','pdf_attribute']
        first_row = ['page_no', 'line', 'is_paragraph_end', 'is_heading', 'is_header', 'is_footer', 'is_bullet_head',
                     'is_bullet_body', 'is_image_caption', 'is_table_caption', 'is_table_content', 'is_toc',
                     'is_toc_heading', 'is_page_no', 'is_doc_title', 'pdf_attribute']
        all_rows.append(first_row)
        for attr in pdf_attributes:
            count += 1
            try:
                row = []
                text = attr[0]
                row.append(str(attr[-3]))
                row.append(text)
                for k in range(0, len(first_row) - 3):
                    row.append(0)
                row.append(str(attr))
                # print("attr",str(attr))
                all_rows.append(row)
                if count > 50:
                    break
            except:
                continue
        writer.writerows(all_rows)
    return pdf_attributes
def extract_hyperlinks(pdf_attributes):
    matched=0
    not_matched=0
    link_count=0
    not_found=0
    pdf = pdfrw.PdfReader(pdf_name)
    link_dict = defaultdict(list)
    for page_no, page in enumerate(pdf.pages, 1):  # Go through the pages

        for annot in page.Annots or []:
            if annot['/A']['/URI'] is not None:
                link_count+=1
                rect_coords = (float(annot['/Rect'][1]), float(annot['/Rect'][3]), page_no)

                link_dict[rect_coords].append({'link': annot['/A']['/URI'], 'link_coords': tuple(map(float,annot['/Rect']))})
    pdf_attributes = list(pdf_attributes)
    for link_dict_attr in sorted(link_dict,key=lambda kv:kv[2]):

        for index, pdf_attr in enumerate(pdf_attributes):
            if int(link_dict_attr[2]) == pdf_attr[6] and (
                    int(link_dict_attr[0]) in range(int(pdf_attr[3][1]) - 5, int(pdf_attr[3][1]) + 6)) and (
                    int(link_dict_attr[1]) in range(int(pdf_attr[3][3]) - 5, int(pdf_attr[3][3]) + 6)):

                for link_attr in link_dict[link_dict_attr]:
                    for word_coords,word in sorted(all_word_coords[pdf_attr[0]].items()):
                        if int(link_attr['link_coords'][0]) in range(word_coords[0]-6,word_coords[0]+5) or int(link_attr['link_coords'][2]) in range(word_coords[1]-6,word_coords[1]+5):
                            #print(word,'matched word**************************')
                            #print(link_attr['link'],'matched link')
                            #print(pdf_attr[0],'line')
                            link_attr['matched word']=word
                            matched+=1
                            temp = list(pdf_attr)
                            temp[-1].append(link_attr)
                            temp = tuple(temp)
                            pdf_attributes[index] = temp
                            break
                    else:
                        not_matched+=1
                        '''
                        if all_word_coords[pdf_attr[0]] is {}:
                            print(link_attr, '\n', all_word_coords[pdf_attr[0]], 'in elif')
                            print(pdf_attr[0], 'not matched')
                            print(link_dict_attr, '****')
                        else:

                            print(link_attr, '\n', all_word_coords[pdf_attr[0]], 'in else')
                            print(pdf_attr[0], 'not matched')
                            print(link_dict_attr, '****')
                        '''
                break
        else:
            #print(link_dict_attr,'not found in csv')
            not_found+=1
            #print(pdf_attributes[0][3][1],pdf_attributes[0][3][3],pdf_attributes[0][6])



    '''
    print('total links:',link_count)
    print('links matched',matched)
    print('links not matched',not_matched)
    print('links not found',not_found)
    '''

    pdf_attributes = tuple(pdf_attributes)
    return pdf_attributes

# generate_pdf_attributes_csv()
