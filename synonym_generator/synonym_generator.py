import syn_gen_with_docs as sgdocs
import syn_gen_with_kg_answers as sgans
import syn_gen_with_googlenews as sgnews
import json
import sys
import argparse

def preprocess(terms):
    new_terms = list()
    for term in terms:
        try:
            if isinstance(term,dict):
                subterms = term.get('name').split('/')
            else:
                subterms = term.split('/')
            for subterm in subterms:
                if ':' in subterm:
                    subterm = subterm.split(':')[0]
                new_terms.append(subterm.strip('**').strip('!!'))
        except:
            print('EXCEPTION')
            continue
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

def synonym_generation_master(file_name, pdf_file=None, pretrained_model = False, type = 'pdf'):
    words = retrieve_words(file_name)
    if pretrained_model != False:
        sgnews.fetch_synonyms(words, file_name, pretrained_model)
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
    parser.add_argument('--training_data_path', help='path for input pdf file or zip containing pdfs or the path to the pretrained model', default=None)
    parser.add_argument('--training_data_type', help='type of training data, pdf or zip or pretrained', default='pdf')

    _input_arguments = parser.parse_args()


    file_name = _input_arguments.file_path
    training_data_path = _input_arguments.training_data_path 
    type = _input_arguments.training_data_type

    if type == 'pretrained':
        synonym_generation_master(file_name, pretrained_model = training_data_path)
    else:
        synonym_generation_master(file_name, pdf_file=training_data_path, type=type)