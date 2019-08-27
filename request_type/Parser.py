import json
import abc
import traceback

from StopWords import StopWords
from log.Logger import Logger
from phrase_finder import PhraseFinder
from StringProcessor import StringProcessor

logger = Logger()
phrase_finder = PhraseFinder()
string_processor = StringProcessor()


class Parser(object, metaclass=abc.ABCMeta):

    def __init__(self, args):
        self.args = args
        logger.info(json.dumps({'Generation_Request': self.args}, indent=2))
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
