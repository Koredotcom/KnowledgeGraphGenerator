from itertools import count as it_count
from collections import namedtuple
from strategy.phrase_finder import PhraseFinder
from request_type.Parser import Parser
from log.Logger import Logger
from common import get_answer_object
import copy
import traceback

logger = Logger()
phrase_finder = PhraseFinder()


class CSVParser(Parser):

    def parse(self):
        response = dict()
        self.faq_payload = self.read_file('csv')
        self.print_verbose('pre processing input data ...')
        stop_tokens = self.get_stopwords()
        questions_map, ques_to_altq_map = self.create_question_maps()
        response['question_map'] = questions_map
        response['altq_map'] = ques_to_altq_map
        response['stop_words'] = stop_tokens
        return response

    @staticmethod
    def prepare_answer_object(answer_text):
        answer_object = get_answer_object()
        answer_object[0]['text'] = answer_text
        answer_object[0]['type'] = 'basic'
        answer_object[0]['channel'] = 'default'
        return answer_object

    def create_question_maps(self):
        logger.info('Creating question maps')
        question_id_map = dict()
        ques_to_altq_id_map = dict()
        try:
            id_generator = it_count(start=10001, step=1)
            qna_record = namedtuple('qna', ['question', 'normalized_ques', 'answer', 'subAnswers', 'response_type'])
            for qna in self.faq_payload:
                primary_ques = qna[0]
                answer_obj = self.prepare_answer_object(qna[1])
                answer_payload = copy.deepcopy(answer_obj)
                sub_answer_payload = list()

                primary_ques_id = next(id_generator)
                question_id_map[primary_ques_id] = qna_record(primary_ques, self.normalize_string(primary_ques),
                                                              answer_payload, sub_answer_payload, 'message')
                ques_to_altq_id_map[primary_ques_id] = []
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            return question_id_map, ques_to_altq_id_map
