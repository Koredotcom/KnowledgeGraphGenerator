from log.Logger import Logger
from common import JSON_TEMPLATE, get_answer_object
import copy
import json
import traceback

logger = Logger()


class JSONGenerator(object):
    def __init__(self):
        pass

    @staticmethod
    def write_response_to_file(response_content, file_path):
        try:
            with open(file_path, 'w') as fp:
                json.dump(response_content, fp)
            msg_string = 'saved file content in filepath - {}\n'.format(file_path)
            logger.info(msg_string)
            return file_path
        except Exception:
            logger.error(traceback.format_exc())

    @staticmethod
    def create_response(response_object):
        questions_map = response_object.get('question_map', dict())
        ques_to_altq_map = response_object.get('altq_map', dict())
        tag_term_map = response_object.get('tag_term_map', dict())
        response = {'faqs': [], 'synonyms': response_object.get('graph_synonyms', dict())}
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
                    cur_sub_answer = list()
                    for ext_answer in alt_answer:
                        answer_obj = get_answer_object()[0]
                        answer_obj['text'] = ext_answer.get('text', 'test')
                        answer_obj['type'] = ext_answer.get('type')
                        answer_obj['channel'] = ext_answer.get('channel')
                        cur_sub_answer.append(copy.deepcopy(answer_obj))
                    result['alternateAnswers'].append(cur_sub_answer)

                if result.get('responseType', 'message') == 'dialog':
                    result['dialogRefId'] = ""

                response['faqs'].append(result)

            return response
        except Exception:
            logger.error(traceback.format_exc())
            raise Exception('Failed in creating final response')
