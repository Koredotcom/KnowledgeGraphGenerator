import traceback
from collections import namedtuple, defaultdict
from itertools import count as it_count

from log.Logger import Logger
from request_type.Parser import StopWords, Parser
from strategy.phrase_finder import PhraseFinder

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
            response['graph_synonyms'] = self.update_generated_synonyms(self.args['syn_file_path'], self.get_graph_level_synonyms())
            return response
        except Exception:
            error_msg = traceback.format_exc()
            logger.error(error_msg)
            self.print_verbose(error_msg)

    def get_graph_level_synonyms(self):
        synonyms = self.faq_payload.get('synonyms', {})
        return synonyms

    def get_stopwords_for_json(self):
        try:
            if 'kgParams' in self.faq_payload and self.faq_payload['kgParams'].get('stopWords', []):
                stop_words = set(self.faq_payload.get('kgParams').get('stopWords'))
                if self.args.get('lang_code', '') == 'en':  # NLP-7736
                    stop_words.update(StopWords.english_question_words)
                return stop_words
            else:
                msg = "json export doesn't have stopwords, considering default stopwords ..."
                logger.info(msg)
                self.print_verbose(msg)
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
                                                              answer_payload, sub_answer_payload,
                                                              qna.get('responseType'))
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

    def update_generated_synonyms(self, generated_syn_path, graph_level_synonyms):
        if generated_syn_path:
            try:
                generated_synonyms = self.read_file_csv(generated_syn_path)
                result = defaultdict(list)
                for key in graph_level_synonyms:
                    result[key] = graph_level_synonyms[key]
                for row in generated_synonyms:
                    if len(row) > 1:
                        synonyms = []
                        key = row[0]
                        for val in row[1].split('/'):
                            val = val.strip()
                            if val:
                                synonyms.append(val)
                        result[key].extend(synonyms)
                return result
            except Exception:
                logger.error(traceback.format_exc())
                return graph_level_synonyms
        else:
            return graph_level_synonyms
