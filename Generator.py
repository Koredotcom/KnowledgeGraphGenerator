import json
import re
import abc
import traceback

from StopWords import StopWords
from log.Logger import Logger
from phrase_finder import PhraseFinder
from OntologyGenerator import OntologyGenerator
from common import *

logger = Logger()
phrase_finder = PhraseFinder()


class StringProcessor(object):
    """ language specific string operations"""

    def __init__(self):
        self.contractions_dict = {
            "can't've": "cannot have",
            "couldn't've": "could not have",
            "hadn't've": "had not have",
            "he'd've": "he would have",
            "he'll've": "he will have",
            "how'd'y": "how do you",
            "i'd've": "i would have",
            "i'll've": "i will have",
            "it'd've": "it would have",
            "it'll've": "it will have",
            "mightn't've": "might not have",
            "mustn't've": "must not have",
            "needn't've": "need not have",
            "oughtn't've": "ought not have",
            "sha'n't": "shall not",
            "shan't've": "shall not have",
            "she'd've": "she would have",
            "she'll've": "she will have",
            "shouldn't've": "should not have",
            "that'd've": "that would have",
            "there'd've": "there would have",
            "they'd've": "they would have",
            "they'll've": "they will have",
            "we'd've": "we would have",
            "we'll've": "we will have",
            "what'll've": "what will have",
            "who'll've": "who will have",
            "won't've": "will not have",
            "wouldn't've": "would not have",
            "y'all'd": "you all would",
            "y'all're": "you all are",
            "y'all've": "you all have",
            "you'd've": "you would have",
            "you'll've": "you will have",
            "ain't": "is not",
            "aren't": "are not",
            "can't": "cannot",
            "'cause": "because",
            "could've": "could have",
            "couldn't": "could not",
            "didn't": "did not",
            "doesn't": "does not",
            "don't": "do not",
            "hadn't": "had not",
            "hasn't": "has not",
            "haven't": "have not",
            "he'd": "he would",
            "he'll": "he will",
            "he's": "he is",
            "how'd": "how did",
            "how'll": "how will",
            "how's": "how is",
            "i'd": "i would",
            "i'll": "i will",
            "i'm": "i am",
            "i've": "i have",
            "isn't": "is not",
            "it'd": "it would",
            "it'll": "it will",
            "it's": "it is",
            "let's": "let us",
            "ma'am": "madam",
            "mayn't": "may not",
            "might've": "might have",
            "mightn't": "might not",
            "must've": "must have",
            "mustn't": "must not",
            "needn't": "need not",
            "o'clock": "of the clock",
            "oughtn't": "ought not",
            "shan't": "shall not",
            "she'd": "she would",
            "she'll": "she will",
            "she's": "she is",
            "should've": "should have",
            "shouldn't": "should not",
            "so've": "so have",
            "so's": "so is",
            "that'd": "that had",
            "that's": "that is",
            "there'd": "there would",
            "there's": "there is",
            "they'd": "they would",
            "they'll": "they will",
            "they're": "they are",
            "they've": "they have",
            "to've": "to have",
            "wasn't": "was not",
            "we'd": "we would",
            "we'll": "we will",
            "we're": "we are",
            "we've": "we have",
            "weren't": "were not",
            "what'll": "what will",
            "what're": "what are",
            "what's": "what is",
            "what've": "what have",
            "when's": "when is",
            "when've": "when have",
            "where'd": "where did",
            "where's": "where is",
            "where've": "where have",
            "who'll": "who will",
            "who's": "who is",
            "who've": "who have",
            "why's": "why is",
            "why've": "why have",
            "will've": "will have",
            "won't": "will not",
            "would've": "would have",
            "wouldn't": "would not",
            "y'all": "you all",
            "you'd": "you would",
            "you'll": "you will",
            "you're": "you are",
            "you've": "you have"""
        }

        self.contractions_re = re.compile(
            '(%s)' %
            '|'.join(list(self.contractions_dict.keys())), re.IGNORECASE)

    def expand_contractions(self, input_string):
        """ expand standard english language contractions """
        try:
            def replace(match):
                """ replace matched string"""
                return self.contractions_dict[match.group(0).lower()]

            return self.contractions_re.sub(replace, input_string)
        except:
            return input_string

    def normalize(self, input_string, language_code):
        """ clean the input string"""
        return_string = input_string.lower()
        if language_code == 'en':
            expanded_string = self.expand_contractions(return_string)
            if expanded_string.find("'") != -1:
                expanded_string = self.expand_contractions(expanded_string)

            return_string = re.sub(
                r'\W+',
                ' ',
                expanded_string)  # Remove Non AlphaNumeric Character

        return return_string


string_processor = StringProcessor()


class Generator(object, metaclass=abc.ABCMeta):

    def __init__(self, args):
        self.args = args
        logger.info(json.dumps({'Generation_Request': self.args}, indent=2))
        self.stop_tokens = set()
        self.faq_payload = dict()

    @abc.abstractmethod
    def read_input_from_file(self):
        pass

    @abc.abstractmethod
    def create_question_maps(self):
        pass

    def save_to_file(self, file_content):
        try:
            output_file_path = self.args.get('output_file_path')
            with open(output_file_path, 'w') as fp:
                json.dump(file_content, fp)
            msg_string = 'saved file content in filepath - {}\n'.format(output_file_path)
            logger.info(msg_string)
            self.print_verbose(msg_string)
            return output_file_path
        except Exception:
            logger.error(traceback.format_exc())
            self.print_verbose('Failed saving response as json')

    def get_stopwords(self):
        lang = 'en_kore' if self.args.get('lang_code') == 'en' else self.args.get('lang_code')
        return StopWords.get_stop_words(lang)

    def print_verbose(self, statement):
        if self.args.get('verbose', False):
            print(statement)

    def normalize_string(self, input_string):
        return string_processor.normalize(input_string, self.args.get('lang_code'))

    def create_response_json(self, questions_map, ques_to_altq_map, tag_term_map):
        response = {'faqs': []}
        try:
            logger.info('Creating response json')
            for ques_id in ques_to_altq_map:
                qna_obj = questions_map.get(ques_id)
                result = copy.deepcopy(JSON_TEMPLATE)
                result['question'] = qna_obj.question
                result['terms'] = tag_term_map[ques_id].get('terms')
                result['tags'] = tag_term_map[ques_id].get('tags')
                result['responseType'] = qna_obj.response_type

                for primary_ans in qna_obj.answer:
                    answer_obj = get_answer_object()[0]
                    answer_obj['text'] = primary_ans.get('text', 'test')
                    answer_obj['type'] = primary_ans.get('type')
                    answer_obj['channel'] = primary_ans.get('channel')
                    result['answer'].append(copy.deepcopy(answer_obj))

                for alt_ques_id in ques_to_altq_map.get(ques_id, []):
                    alt_qna_result = dict()
                    alt_qna_obj = questions_map.get(alt_ques_id)
                    alt_qna_result['question'] = alt_qna_obj.question
                    alt_tags = list(set(tag_term_map.get(alt_ques_id).get('terms')).difference(set(result['terms'])))
                    alt_qna_result['tags'] = tag_term_map.get(alt_ques_id).get('tags') + copy.deepcopy(alt_tags)
                    alt_qna_result['terms'] = tag_term_map[ques_id].get('terms')
                    result['alternateQuestions'].append(copy.deepcopy(alt_qna_result))

                for alt_answer in qna_obj.subAnswers:
                    answer_obj = get_answer_object()
                    answer_obj[0]['text'] = alt_answer[0].get('text', 'test')
                    answer_obj[0]['type'] = alt_answer[0].get('type')
                    answer_obj[0]['channel'] = alt_answer[0].get('channel')
                    result['alternateAnswers'].append(copy.deepcopy(answer_obj))

                response['faqs'].append(result)

            return self.save_to_file(response)
        except Exception:
            logger.error(traceback.format_exc())
            raise Exception('Failed in creating final response')

    def generate_ontology_from_phrases(self, questions_map, ques_to_altq_map):
        try:
            logger.info("finding phrases and terms")
            phrases, uni_tokens, verbs = phrase_finder.find_all_phrases(questions_map, self.stop_tokens)
            ontology_generator = OntologyGenerator(self.stop_tokens)
            tag_term_map = ontology_generator.process_qna(phrases, uni_tokens, verbs, questions_map)
            response_file_path = self.create_response_json(questions_map, ques_to_altq_map, tag_term_map)
            print('Ontology generated successfully and saved in {}'.format(response_file_path))
            return True
        except Exception:
            logger.error(traceback.format_exc())
            return False
