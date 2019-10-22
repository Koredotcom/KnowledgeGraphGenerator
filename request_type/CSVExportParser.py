from itertools import count as it_count
from collections import namedtuple
from request_type.Parser import PhraseFinder, Parser, StopWords
from log.Logger import Logger
from common import get_answer_object
import traceback
import copy

logger = Logger()
phrase_finder = PhraseFinder()


class CSVExportParser(Parser):
    def parse(self):
        response = dict()
        try:
            self.print_verbose('pre processing input data ...')
            self.faq_payload = self.read_file('csv')
            questions_map, ques_to_altq_map, faq_row_count = self.create_question_maps()
            stop_tokens = self.get_stopwords_from_csv(faq_row_count)
            response['question_map'] = questions_map
            response['altq_map'] = ques_to_altq_map
            response['stop_words'] = stop_tokens
            return response
        except Exception:
            error_msg = traceback.format_exc()
            logger.error(error_msg)
            self.print_verbose(error_msg)

    def get_stopwords_from_csv(self, faq_row_counter):
        try:
            for row in self.faq_payload[faq_row_counter + 1:]:
                if row[0] == 'kgParams':
                    stop_words = set(row[4:])
                    if self.args.get('lang_code', '') == 'en':
                        stop_words.update(StopWords.english_question_words)
                    return stop_words
            return self.get_stopwords()
        except Exception:
            logger.error(traceback.format_exc())
            return set()

    def create_question_maps(self):
        logger.info('Creating question maps')
        question_id_map = dict()
        ques_to_altq_id_map = dict()
        faq_row_count = 0
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
                faq_row_count += 1
            return question_id_map, ques_to_altq_id_map, faq_row_count
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
