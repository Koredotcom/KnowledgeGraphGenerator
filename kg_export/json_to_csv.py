import copy
import csv
import json
import traceback
import uuid
from itertools import dropwhile
from kg_export.constants import *
from kg_export.log.Logger import Logger
from kg_export.utils import log_message, get_index

logger = Logger()


class JsonToCsv(object):
    def __init__(self):
        self.node_trait_dict = dict()
        self.faq_row_map = dict()
        self.tag_trait_dict = dict()
        self.root_node = ''
        self.unmapped_path = list()

    def extract_root_node(self, term_payload):
        if term_payload:
            self.root_node = term_payload[0]['terms'][-1]
        else:
            log_message('root node not found in first node', ERROR)

    @staticmethod
    def read_json_file(file_path):
        try:
            with open(file_path, 'r') as fp:
                json_content = json.load(fp)
            return json_content
        except Exception:
            logger.error(traceback.format_exc())

    @staticmethod
    def remove_node_identifiers(node):
        for identifier in NODE_IDENTIFIERS:
            if node.startswith(identifier):
                node = node.lstrip(identifier)
                break
        return node

    def parse_terms(self, nodes_payload, ref_id, is_tag, is_unmapped_path=False):
        processed_nodes = list()
        nodes_for_trait_key = list()
        nodes_payload = [self.root_node] + nodes_payload if self.root_node not in nodes_payload and not is_tag else nodes_payload
        local_nodes_payload = copy.deepcopy(nodes_payload)
        local_nodes_payload.reverse()  # we allow terms order from root in csv
        for node in local_nodes_payload:
            current_node = copy.deepcopy(node)
            current_node, traits = current_node.split(TRAIT_DELIMITER) if TRAIT_DELIMITER in current_node else [current_node, '']
            traits = traits.split(',')
            current_node = current_node.split(SYNONYM_DELIMITER)
            current_node, synonyms = current_node[0], current_node[1:]
            synonym_string = ''
            if synonyms:
                synonym_string = '(' + SYNONYM_DELIMITER.join(synonyms) + ')'

            nodes_for_trait_key.append(self.remove_node_identifiers(current_node))
            processed_nodes.append(current_node + synonym_string)

            # to remove empty strings in traits
            traits = list(reversed(tuple(dropwhile(lambda t: t is '', reversed(traits)))))
            if traits:
                if is_tag:
                    if ref_id:
                        key = ref_id + TRAIT_KEY_DELIMITER + current_node
                        self.tag_trait_dict[key] = traits
                else:
                    key = DEFAULT_DELIMITER.join(nodes_for_trait_key)
                    self.node_trait_dict[key] = traits
                    if is_unmapped_path:
                        self.unmapped_path.append({'terms': nodes_for_trait_key})
        return DEFAULT_DELIMITER.join(processed_nodes)

    @staticmethod
    def parse_answers(answer_object):
        result = list()
        for answer_payload in answer_object:
            answer_list = []
            is_default_channel = True
            is_type_basic = True
            if answer_payload.get('channel', 'default') != 'default':
                is_default_channel = False
                channel_name = CHANNEL_IDENTIFIER + '_' + '_'.join(answer_payload.get('channel').upper().split(' '))
                answer_list.append(channel_name)
            if answer_payload.get('type', 'basic') != 'basic':
                is_type_basic = False
                answer_list.append(SCRIPT_IDENTIFIER)
            if not is_default_channel and is_type_basic:
                answer_list.append(TEXT_IDENTIFIER)

            answer_list.append(answer_payload.get('text'))
            answer_string = ' '.join(answer_list)
            result.append(answer_string)
        return result

    @staticmethod
    def get_unique_id():
        return str(uuid.uuid4())

    def create_csv_faq_row(self, faq_object):
        row_count = max(len(faq_object.get('alternateAnswers', [])), len(faq_object.get('alternateQuestions', []))) + 1
        csv_faq_rows = [[''] * MIN_COL_COUNT for _ in range(row_count)]
        ques_ref_id = faq_object.get('refId', '')
        primary_question = faq_object.get('question', '')
        is_unmapped_path = False if primary_question else True
        terms = self.parse_terms(faq_object.get('terms', []), ques_ref_id, False, is_unmapped_path)
        tags = self.parse_terms(faq_object.get('tags', []), ques_ref_id, True, is_unmapped_path)
        response_type = faq_object.get('responseType', 'message')
        csv_faq_rows[0][QUES_ID_COL_NO] = ques_ref_id
        csv_faq_rows[0][TERM_PATH_COL_NO] = terms
        csv_faq_rows[0][PRIMARY_QUES_COL_NO] = primary_question
        csv_faq_rows[0][TAG_PATH_COL_NO] = tags

        if response_type == 'dialog':
            csv_faq_rows[0][ANS_COL_NO] = DIALOG_IDENTIFIER + ' ' + faq_object.get('dialogRefId')
        else:
            csv_format_answer = self.parse_answers(faq_object.get('answer', []))
            col_index = ANS_COL_NO
            for answer in csv_format_answer:
                csv_faq_rows[0][col_index] = answer
                col_index += 1

        alternate_ques = faq_object.get('alternateQuestions', [])
        for payload_index in range(len(alternate_ques)):
            tag_ref_id = alternate_ques[payload_index].get('refId', '')
            csv_faq_rows[payload_index + 1][QUES_ID_COL_NO] = tag_ref_id
            csv_faq_rows[payload_index + 1][ALT_QUES_COL_NO] = alternate_ques[payload_index].get('question', '')
            csv_faq_rows[payload_index + 1][TAG_PATH_COL_NO] = self.parse_terms(alternate_ques[payload_index].get('tags', []), tag_ref_id, True)

        alternate_answers = faq_object.get('alternateAnswers', [])
        for payload_index in range(len(alternate_answers)):
            csv_format_answer = self.parse_answers(alternate_answers[payload_index])
            col_index = ANS_COL_NO
            for answer in csv_format_answer:
                csv_faq_rows[payload_index + 1][col_index] = answer
                col_index += 1

        csv_faq_rows = list(map(lambda row: list(reversed(tuple(dropwhile(lambda col: col is '', reversed(row))))), csv_faq_rows))
        self.faq_row_map[ques_ref_id] = csv_faq_rows
        return csv_faq_rows

    def parse_faqs(self, faq_payload):
        log_message('Parsing FAQs ... ')
        result = list()
        result.append(FAQ_HEADER)
        for faq_obj in faq_payload:
            try:
                result.extend(self.create_csv_faq_row(faq_obj))
            except Exception:
                log_message('Error while parsing FAQ payload with faq object number - {}'.format(get_index(faq_obj, faq_payload)), ERROR)
                logger.error(traceback.format_exc())
                raise Exception
        result.extend([[''] * SECTION_DELIMITING_COUNT])
        return result

    def parse_nodes(self, node_payload):
        log_message('Parsing FAQ terms ...')
        result = list()
        result.append(NODE_HEADER)
        for node_obj in node_payload:
            try:
                row_body = ['', '']
                terms = node_obj.get('terms', [])[::-1]
                terms = list(map(str.strip, terms))
                node_string = ','.join(terms)

                row_body.append(node_string)
                row_body.append('N')  # terms have default value NO
                row_body.append(','.join(node_obj.get('preConditions', [])))
                row_body.append(','.join(node_obj.get('contextTags', [])))
                traits = DEFAULT_DELIMITER.join(self.node_trait_dict.get(node_string, ''))
                row_body.append(traits)
                result.append(row_body)
            except Exception:
                log_message('Error while parsing node payload with node object index - {}'.format(get_index(node_obj, node_payload)), ERROR)
                logger.error(traceback.format_exc())
                raise Exception

        return result

    def parse_tags(self, tag_payload):
        log_message('Parsing FAQ tags ...')
        result = list()
        for question_tags in tag_payload:
            ref_id = question_tags.get('refId')
            tag_list = question_tags.get('tags', [])
            for tag_body in tag_list:
                try:
                    csv_row = ['', ref_id]
                    tag_name = tag_body.get('name')
                    preconditions = DEFAULT_DELIMITER.join(tag_body.get('preConditions', []))
                    context_tags = DEFAULT_DELIMITER.join(tag_body.get('contextTags', []))
                    csv_row.append(tag_name)
                    csv_row.append('Y')
                    csv_row.append(preconditions)
                    csv_row.append(context_tags)
                    trait_key = ref_id + TRAIT_KEY_DELIMITER + tag_name
                    traits = DEFAULT_DELIMITER.join(self.tag_trait_dict.get(trait_key, ''))
                    csv_row.append(traits)
                    result.append(csv_row)
                except Exception:
                    log_message('Error while parsing Tag payload with tag payload index {} and ref-id {}'.format(get_index(question_tags, tag_payload), ref_id), ERROR)
                    logger.error(traceback.format_exc())
                    raise Exception

        result.extend([[''] * SECTION_DELIMITING_COUNT])
        return result

    @staticmethod
    def parse_kg_synonyms(global_syn_payload):
        log_message('Parsing global synonyms ...')
        result = list()
        result.append(SYNONYMS_HEADER)
        for key in global_syn_payload:
            try:
                csv_row = [''] * 2
                csv_row.append(key)

                csv_row.append(DEFAULT_DELIMITER.join(global_syn_payload[key]))
                result.append(csv_row)
            except Exception:
                log_message('Error while synonym payload for phrase - {}'.format(key), ERROR)
                logger.error(traceback.format_exc())
                raise Exception

        result.extend([[''] * SECTION_DELIMITING_COUNT])
        return result

    @staticmethod
    def parse_kg_params(kg_params):
        log_message('Parsing kg params ...')
        result = list()
        result.append(KG_PARAMS_HEADER)
        if kg_params:
            try:
                params_payload = list()
                params_payload.extend([''] * 2)
                for key in kg_params:
                    if not kg_params[key]:
                        kg_params[key] = ''
                stopwords = DEFAULT_DELIMITER.join(kg_params.get('stopWords', ''))
                language_code = kg_params.get('lang')
                params_payload.append(language_code)
                params_payload.append(stopwords)
                result.append(params_payload)
                result.extend([[''] * SECTION_DELIMITING_COUNT])
            except Exception:
                log_message('Error while parsing kg params payload', ERROR)
                logger.error(traceback.format_exc())
                raise Exception
        return result

    @staticmethod
    def parse_trait_groups(trait_groups):
        log_message('Parsing trait groups ...')
        result = [TRAIT_GROUP_HEADER]
        for group in trait_groups:
            try:
                current_row = [''] * 8
                current_row[2] = group.get('language')
                current_row[3] = group.get('groupName')
                current_row[4] = group.get('matchStrategy', '')
                current_row[5] = group.get('scoreThreshold', 0.5)
                for trait_dict in group.get('traits', {}).values():
                    try:
                        current_row[6] = trait_dict.get('displayName', '')
                        for data_item in trait_dict.get('data', []):
                            current_row[7] = data_item
                            result.append(copy.deepcopy(current_row))
                            current_row = [''] * 8

                        current_row = [''] * 8
                    except Exception:
                        log_message('Error while parsing trait- {} with group name - {}'.format(current_row[6], group.get('groupName', '')), ERROR)
                        logger.error(traceback.format_exc())
                        raise Exception

            except Exception:
                log_message('Error while parsing trait groups with group name - {}'.format(group.get('groupName', '')), ERROR)
                logger.error(traceback.format_exc())
                raise Exception

        return result

    @staticmethod
    def write_csv(file_content, file_loc):
        try:
            with open(file_loc, 'w') as fp:
                csv_writer = csv.writer(fp)
                for row in file_content:
                    csv_writer.writerow(row)
        except Exception:
            log_message('Failed writing json content to csv', ERROR)
            logger.error(traceback.format_exc())

    def parse(self, input_file_path, output_file_path):
        csv_file_content = list()
        try:
            file_content = self.read_json_file(input_file_path)
            self.extract_root_node(file_content.get('nodes', []))
            faqs = self.parse_faqs(file_content.get('faqs', []) + file_content.get('unmappedpath', []))
            nodes = self.parse_nodes(file_content.get('nodes', []))
            tags = self.parse_tags(file_content.get('faqtags', []))
            kg_synonyms = self.parse_kg_synonyms(file_content.get('synonyms', []))
            kg_params = self.parse_kg_params(file_content.get('kgParams', {}))
            trait_groups = self.parse_trait_groups(file_content.get('traitGroups', {}))

            csv_file_content.extend(faqs)
            csv_file_content.extend(nodes)
            csv_file_content.extend(tags)
            csv_file_content.extend(kg_synonyms)
            csv_file_content.extend(kg_params)
            csv_file_content.extend(trait_groups)

            self.write_csv(csv_file_content, output_file_path)
            log_message('New CSV created in {}'.format(output_file_path))
        except Exception:
            log_message('Failed creating CSV from json file', ERROR)
            logger.error(traceback.format_exc())


if __name__ == '__main__':
    file_path = '/home/satyaaditya/Downloads/consistency -  Knowledge Collection.json'
    # file_path = '/home/satyaaditya/Downloads/trim.json'
    # file_path = '/home/satyaaditya/Downloads/consistency -  Knowledge Collection.json'
    # file_path = '/home/satyaaditya/Downloads/airbus csv -  Knowledge Collection (1).json'
    json_reader = JsonToCsv()
    json_reader.parse(file_path, 'eexport.csv')
