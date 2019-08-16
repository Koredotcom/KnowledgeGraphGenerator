import csv
import traceback
from itertools import count as it_count
from collections import namedtuple

from phrase_finder import PhraseFinder
from Generator import Generator
from log.Logger import Logger
from common import *

logger = Logger()
phrase_finder = PhraseFinder()


class CSVExportParser(Generator):
    def parse_and_generate(self):
        self.faq_row_counter = 0
        try:
            self.print_verbose('pre processing input data ...')
            self.faq_payload = self.read_input_from_file()
            questions_map, ques_to_altq_map = self.create_question_maps()
            self.stop_tokens = self.get_stopwords_from_csv()
            self.print_verbose('generating ontology from the data ...')
            self.generate_ontology_from_phrases(questions_map, ques_to_altq_map)
        except Exception:
            error_msg = traceback.format_exc()
            logger.error(error_msg)
            self.print_verbose(error_msg)

    def get_stopwords_from_csv(self):
        for row in self.faq_payload[self.faq_row_counter + 1:]:
            if row[0] == 'kgParams':
                return set(row[4:])
            else:
                return self.get_stopwords()

    def read_input_from_file(self):
        csv_data = list()
        try:
            with open(self.args.get('input_file_path'), 'r') as fp:
                csv_reader = csv.reader(fp)
                for row in csv_reader:
                    csv_data.append(row)
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            return csv_data

    def create_question_maps(self):
        question_id_map = dict()
        ques_to_altq_id_map = dict()
        prev_primary_ques_id = None
        try:
            qna_record = namedtuple('qna', ['question', 'normalized_ques', 'answer', 'subAnswers', 'response_type'])
            id_generator = it_count(start=10001, step=1)
            for row in self.faq_payload:
                if row[0] == 'faq':
                    if row[2] == 'primary':
                        primary_ques_id = next(id_generator)
                        prev_primary_ques_id = copy.deepcopy(primary_ques_id)
                        primary_ques = row[3]
                        answer_obj = self.prepare_answer_object(row[4])
                        answer_payload = copy.deepcopy(answer_obj)
                        sub_answer_payload = list()
                        question_id_map[primary_ques_id] = qna_record(primary_ques, self.normalize_string(primary_ques),
                                                                      answer_payload, sub_answer_payload, 'message')
                        ques_to_altq_id_map[primary_ques_id] = []

                    elif row[2] == 'alternate':
                        alt_ques_id = next(id_generator)
                        alt_ques = row[3]
                        question_id_map[alt_ques_id] = qna_record(alt_ques, self.normalize_string(alt_ques), [], [], '')
                        ques_to_altq_id_map[prev_primary_ques_id].append(alt_ques_id)
                else:
                    break
                self.faq_row_counter += 1
            return question_id_map, ques_to_altq_id_map
        except Exception:
            logger.error(traceback.format_exc())
            self.print_verbose('Failed in pre processing input')


    @staticmethod
    def prepare_answer_object(answer_text):
        answer_object = get_answer_object()
        answer_object[0]['text'] = answer_text
        answer_object[0]['type'] = 'basic'
        answer_object[0]['channel'] = 'default'
        return answer_object
