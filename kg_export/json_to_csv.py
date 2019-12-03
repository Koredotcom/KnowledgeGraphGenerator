import copy
import csv
import json
import traceback
import uuid
from itertools import dropwhile
from kg_export.constants import *


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
            raise Exception

    @staticmethod
    def read_json_file(file_path):
        with open(file_path, 'r', encoding='utf-8') as fp:
            json_content = json.load(fp)
        return json_content

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
        try:
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

        except Exception:
            print(traceback.format_exc())

    def parse_faqs(self, faq_payload):
        print('parsing FAQs ... ')
        result = list()
        result.append(FAQ_HEADER)
        i = 0
        for faq_obj in faq_payload:
            result.extend(self.create_csv_faq_row(faq_obj))
            i += 1
        result.extend([[''] * SECTION_DELIMITING_COUNT])
        return result

    def parse_nodes(self, node_payload):
        print('parsing FAQ terms ...')
        result = list()
        result.append(NODE_HEADER)
        for node_obj in node_payload:
            row_body = ['', '']
            terms = node_obj.get('terms', [])[::-1]
            node_string = ','.join(terms)

            row_body.append(node_string)
            row_body.append('N')  # terms have default value NO
            row_body.append(','.join(node_obj.get('preConditions', [])))
            row_body.append(','.join(node_obj.get('contextTags', [])))
            traits = DEFAULT_DELIMITER.join(self.node_trait_dict.get(node_string, ''))
            row_body.append(traits)
            result.append(row_body)
        return result

    def parse_tags(self, tag_payload):
        print('parsing FAQ tags ...')
        result = list()
        for question_tags in tag_payload:
            ref_id = question_tags.get('refId')
            tag_list = question_tags.get('tags', [])
            for tag_body in tag_list:
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
        result.extend([[''] * SECTION_DELIMITING_COUNT])
        return result

    @staticmethod
    def parse_global_synonyms(global_syn_payload):
        print('parsing global synonyms ...')
        result = list()
        result.append(SYNONYMS_HEADER)
        for key in global_syn_payload:
            csv_row = [''] * 2
            csv_row.append(key)

            csv_row.append(DEFAULT_DELIMITER.join(global_syn_payload[key]))
            result.append(csv_row)

        result.extend([[''] * SECTION_DELIMITING_COUNT])
        return result

    @staticmethod
    def parse_kg_params(kg_params):
        print('parsing stopwords ...')
        result = list()
        if kg_params:
            result.append(KG_PARAMS_HEADER)
            params_payload = list()
            params_payload.extend([''] * 2)
            stopwords = DEFAULT_DELIMITER.join(kg_params.get('stopWords', ''))
            language_code = kg_params.get('lang')
            params_payload.append(language_code)
            params_payload.append(stopwords)
            result.append(params_payload)
            result.extend([[''] * SECTION_DELIMITING_COUNT])
        return result

    def parse_trait_groups(self, trait_groups):
        print('parsing trait groups ...')
        result = []
        if trait_groups:
            result.append(TRAIT_GROUP_HEADER)
        for group in trait_groups:
            current_row = [''] * 8
            current_row[2] = group.get('language')
            current_row[3] = group.get('groupName')
            current_row[4] = group.get('matchStrategy', '')
            current_row[5] = group.get('scoreThreshold', 0.5)
            for trait_dict in group.get('traits', {}).values():
                current_row[6] = trait_dict.get('displayName', '')
                for data_item in trait_dict.get('data', []):
                    current_row[7] = data_item
                    result.append(copy.deepcopy(current_row))
                    current_row = [''] * 8
                else:
                    result.append(copy.deepcopy(current_row))

                current_row = [''] * 8

        return result

    @staticmethod
    def write_csv(file_content, file_loc='kg_export/export.csv'):
        with open(file_loc, 'w') as fp:
            csv_writer = csv.writer(fp)
            for row in file_content:
                csv_writer.writerow(row)
        print('csv generated')

    def parse(self, file_path):
        csv_file_content = list()
        file_content = self.read_json_file(file_path)
        self.extract_root_node(file_content.get('nodes', []))
        faqs = self.parse_faqs(file_content.get('faqs', []) + file_content.get('unmappedpath', []))
        nodes = self.parse_nodes(file_content.get('nodes', []))
        tags = self.parse_tags(file_content.get('faqtags', []))
        global_synonyms = self.parse_global_synonyms(file_content.get('synonyms', []))
        kg_params = self.parse_kg_params(file_content.get('kgParams', {}))
        trait_groups = self.parse_trait_groups(file_content.get('traitGroups', {}))

        csv_file_content.extend(faqs)
        csv_file_content.extend(nodes)
        csv_file_content.extend(tags)
        csv_file_content.extend(global_synonyms)
        csv_file_content.extend(kg_params)
        csv_file_content.extend(trait_groups)

        self.write_csv(csv_file_content)
        print('New csv created with filename export.csv in current working directory')


if __name__ == '__main__':
    file_path = '/home/satyaaditya/Downloads/hiui -  Knowledge Collection.json'
    # file_path = '/home/satyaaditya/Downloads/trim.json'
    # file_path = '/home/satyaaditya/Downloads/consistency -  Knowledge Collection.json'
    # file_path = '/home/satyaaditya/Downloads/airbus csv -  Knowledge Collection (1).json'
    json_reader = JsonToCsv()
    json_reader.parse(file_path)
