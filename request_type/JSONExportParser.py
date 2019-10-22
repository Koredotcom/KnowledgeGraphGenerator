from itertools import count as it_count
from collections import namedtuple
from request_type.Parser import StopWords, Parser
from log.Logger import Logger
from strategy.phrase_finder import PhraseFinder
import traceback

logger = Logger()
phrase_finder = PhraseFinder()


class JSONExportParser(Parser):

    def parse(self):
        try:
            response = dict()
            self.faq_payload = self.read_file('json')
            self.print_verbose('pre processing input data ...')
            stop_tokens = self.get_stopwords_for_json()
            questions_map, ques_to_altq_map = self.create_question_maps()
            response['question_map'] = questions_map
            response['altq_map'] = ques_to_altq_map
            response['stop_words'] = stop_tokens
            return response
        except Exception:
            error_msg = traceback.format_exc()
            logger.error(error_msg)
            self.print_verbose(error_msg)

    def get_stopwords_for_json(self):
        try:
            if 'kgParams' in self.faq_payload:
                stop_words = set(self.faq_payload.get('kgParams').get('stopWords'))
                if self.args.get('lang_code','') == 'en':
                    stop_words.update(StopWords.english_question_words)
                return stop_words
            else:
                return self.get_stopwords()
        except Exception:
            logger.error(traceback.format_exc())
            return set()

    def create_question_maps(self):
        question_id_map = dict()
        ques_to_altq_id_map = dict()
        try:
            logger.info('Creating question maps')
            id_generator = it_count(start=10001, step=1)
            qna_record = namedtuple('qna', ['question', 'normalized_ques', 'answer', 'subAnswers', 'response_type'])
            for qna in self.faq_payload.get('faqs'):
                primary_ques = qna['question']
                alt_ques_payload = qna.get('alternateQuestions', list())
                answer_payload = qna.get('answer', list())
                sub_answer_payload = qna.get('alternateAnswers', list())

                primary_ques_id = next(id_generator)
                question_id_map[primary_ques_id] = qna_record(primary_ques, self.normalize_string(primary_ques),
                                                              answer_payload, sub_answer_payload, qna.get('responseType'))
                ques_to_altq_id_map[primary_ques_id] = []
                for sub_ques in alt_ques_payload:
                    alt_ques_id = next(id_generator)
                    alt_ques = sub_ques.get('question')
                    question_id_map[alt_ques_id] = qna_record(alt_ques, self.normalize_string(alt_ques), [], [], '')
                    ques_to_altq_id_map[primary_ques_id].append(alt_ques_id)

            return question_id_map, ques_to_altq_id_map
        except Exception:
            logger.error(traceback.format_exc())
            self.print_verbose('Failed in pre processing input')
