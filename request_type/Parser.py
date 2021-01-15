import json
import abc
import traceback
import csv

from StopWords import StopWords
from log.Logger import Logger
from strategy.phrase_finder import PhraseFinder
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
    def create_question_maps(self):
        pass

    @staticmethod
    def read_file_json(file_path):
        json_data = dict()
        try:
            with open(file_path, 'r', encoding='utf-8') as fp:
                json_data = json.load(fp)
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            return json_data

    @staticmethod
    def read_file_csv(file_path):
        csv_data = list()
        try:
            with open(file_path, 'r', encoding='utf-8') as fp:
                csv_reader = csv.reader(fp)
                for row in csv_reader:
                    csv_data.append(row)
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            return csv_data

    def read_file(self, file_type):
        file_path = self.args.get('input_file_path')
        if file_type == 'json':
            return self.read_file_json(file_path)
        elif file_type == 'csv':
            return self.read_file_csv(file_path)

    def save_file(self, file_content):
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
        lang = self.args.get('lang_code')
        return StopWords.get_stop_words(lang)

    def print_verbose(self, statement):
        if self.args.get('verbose', False):
            print(statement)

    def normalize_string(self, input_string):
        return string_processor.normalize(input_string, self.args.get('lang_code'))
