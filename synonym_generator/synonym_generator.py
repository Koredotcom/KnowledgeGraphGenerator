import syn_gen_with_docs as sgdocs
import syn_gen_with_kg_answers as sgans
import syn_gen_with_googlenews as sgnews
import json
import sys
import argparse

def preprocess(terms):
    new_terms = list()
    for term in terms:
        subterms = term.split('/')
        for subterm in subterms:
            if ':' in subterm:
                subterm = subterm.split(':')[0]
            new_terms.append(subterm.strip('**').strip('!!'))

    return new_terms

def retrieve_words(file_name):
    faq_terms = set()
    faq_tags = set()

    with open(file_name) as json_data:
        json_faqs = json.load(json_data)
        faqs = json_faqs['faqs']
        c = 0
        considered = set()
        for faq in faqs:
            if not 'answer' in faq  or faq['answer'][0]['text'] in considered:
                continue
            faq_terms |= set(preprocess(faq['terms']))
            faq_tags |= set(preprocess(faq['tags']))
            considered.add(faq['answer'][0]['text'])
            c += 1
    return faq_tags | faq_terms

def synonym_generation_master(file_name, pdf_file=None, use_google_news = False, type = 'pdf'):
    words = retrieve_words(file_name)
    if use_google_news:
        sgnews.fetch_synonyms(words, file_name)
    elif pdf_file is None:
        sgans.fetch_synonyms(words, file_name)
    else:
        if type == 'pdf':
            sgdocs.fetch_synonyms(words, pdf_file)
        elif type == 'zip':
            sgdocs.fetch_synonyms(words, pdf_file, zip_mode = True)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', help='path for input json file')
    parser.add_argument('--training_data_path ', help='path for input pdf file or zip containing pdfs', default=None)
    parser.add_argument('--type ', help='type of training data, pdf or zip', default='pdf')
    parser.add_argument('--use_google_news', help='use googlenews-based pretrained word2vec model', default=False)

    _input_arguments = parser.parse_args()


    file_name = _input_arguments.file_path
    pdf_file = _input_arguments.training_data_path 
    use_google_news = _input_arguments.use_google_news
    type = _input_arguments.type

    if bool(use_google_news):
        synonym_generation_master(file_name, use_google_news = True)
    else:
        synonym_generation_master(file_name, pdf_file=pdf_file, type=type)