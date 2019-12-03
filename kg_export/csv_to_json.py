import copy
import csv
import json
from collections import defaultdict
from kg_export.constants import *
from itertools import dropwhile


class CsvToJson(object):
    def __init__(self):
        self.faq_data = list()
        self.term_data = list()
        self.global_syn_data = list()
        self.kg_param_data = list()
        self.node_trait_dict = dict()
        self.tag_trait_dict = dict()
        self.unmapped_paths = list()
        self.trait_group_data = list()

    @staticmethod
    def read_csv_file(file_loc):
        result = list()
        with open(file_loc, 'r') as fp:
            csv_reader = csv.reader(fp)
            for row in csv_reader:
                result.append(row)
        return result

    def group_csv_data(self, csv_data):
        current_container = None
        is_section_present = False
        csv_container = {'faq': self.faq_data, 'node': self.term_data, 'synonyms': self.global_syn_data,
                         'kg params': self.kg_param_data, 'traits': self.trait_group_data}
        for row in csv_data:
            if row[0].lower() in VALID_SECTIONS:
                is_section_present = True
                current_container = csv_container[row[0].lower()]
            else:
                if current_container is not None:
                    current_container.append(row)
                else:
                    print('container not found')
        if not is_section_present:
            print('No valid sections present in faq')

    def parse_nodes(self):
        print('parsing FAQ terms and tags ...')
        node_payload = list()
        tag_payload = defaultdict(list)
        for row in self.term_data:
            term_object = dict()
            row_copy = dict(enumerate(row))
            terms = row_copy.get(TERM_PATH_COL_NO, '').split(DEFAULT_DELIMITER)
            preconditions = row_copy.get(TERM_PRECON_INDEX, '')
            context_tags = row_copy.get(TERM_CONTEXT_INDEX, '')
            ref_id = row_copy.get(REF_ID_INDEX, '')
            traits = row_copy.get(TERM_TRAIT_INDEX, '')
            preconditions = preconditions.split(DEFAULT_DELIMITER) if preconditions else []
            context_tags = context_tags.split(DEFAULT_DELIMITER) if context_tags else []
            traits = traits.split(DEFAULT_DELIMITER) if traits else []

            if terms:
                term_object['preConditions'] = preconditions
                term_object['contextTags'] = context_tags
                is_tag = row_copy.get(3, '')
                if is_tag == 'Y' and ref_id:
                    term_object['name'] = terms[0]
                    self.tag_trait_dict[ref_id + TRAIT_KEY_DELIMITER + terms[0]] = traits
                    tag_payload[ref_id].append(copy.deepcopy(term_object))
                elif is_tag == 'N':
                    term_object['terms'] = terms[::-1]
                    self.node_trait_dict[DEFAULT_DELIMITER.join(terms)] = traits
                    node_payload.append(copy.deepcopy(term_object))

        tag_payload = [{'refId': ref_id, 'tags': tag_obj} for ref_id, tag_obj in tag_payload.items()]
        print('traits map for nodes and tags is created')
        return node_payload, tag_payload

    @staticmethod
    def resolve_synonym_format(node):
        node = node.replace('(', '/')
        node = node.replace(')', '')
        return node

    @staticmethod
    def remove_node_identifiers(node):
        for identifier in NODE_IDENTIFIERS:
            if node.startswith(identifier):
                node = node.lstrip(identifier)
                break
        return node

    @staticmethod
    def remove_synonyms_from_nodes(node_list):
        result = list()
        for node in node_list:
            result.append(node.split('/')[0])
        return result

    def get_json_format_paths(self, node_path):
        if node_path:
            nodes = node_path.split(DEFAULT_DELIMITER)
            nodes = list(map(self.resolve_synonym_format, nodes))
            flatten_nodes = self.remove_synonyms_from_nodes(nodes)
            flatten_nodes = [self.remove_node_identifiers(node) for node in flatten_nodes]
            return [nodes, flatten_nodes]
        else:
            return [], []

    def apply_traits_to_path_terms(self, path_list, flatten_path):
        trait_dict = self.node_trait_dict
        node_dict = {node: '' for node in path_list}
        flat_node_string = DEFAULT_DELIMITER.join(flatten_path)
        for trait_path in trait_dict:
            if flat_node_string.startswith(trait_path):
                node_with_trait = trait_path.split(DEFAULT_DELIMITER)[-1]
                node_index = flatten_path.index(node_with_trait)
                node_value = path_list[node_index]
                traits = trait_dict[trait_path]
                traits = ''.join(traits)
                node_dict[node_value] = traits

        path_with_traits = [key + ':' + value if value else key for key, value in node_dict.items()]
        return path_with_traits

    def apply_traits_to_path_tags(self, tag_list, flatten_tags, ref_id):
        if ref_id:
            trait_dict = self.tag_trait_dict
            node_dict = {node: '' for node in tag_list}
            for tag in flatten_tags:
                trait_key = ref_id + TRAIT_KEY_DELIMITER + tag
                if trait_key in trait_dict:
                    traits = trait_dict[trait_key]
                    traits = ''.join(traits)
                    tag_index = flatten_tags.index(tag)
                    tag_value = tag_list[tag_index]
                    node_dict[tag_value] = traits
            tag_with_traits = [key + ':' + value if value else key for key, value in node_dict.items()]
            return tag_with_traits
        return tag_list

    @staticmethod
    def parse_answer(answer_list):
        final_answer_obj = list()
        response_type = 'message'
        for answer in answer_list:
            sub_answer = dict()
            text = copy.deepcopy(answer).strip()
            answer_type = 'basic'
            channel = 'default'
            if text.startswith(DIALOG_IDENTIFIER):
                response_type = 'dialog'
                text = text.replace(DIALOG_IDENTIFIER, '').strip()
                return text, response_type
            else:
                if text.startswith(CHANNEL_IDENTIFIER):
                    text = text.replace(CHANNEL_IDENTIFIER, '')
                    index = text.find(' ')
                    if index != -1:
                        channel, text = text[:index].strip(), text[index + 1:].lstrip()
                        channel = channel.lower().replace('_', ' ').strip()
                    else:
                        print('channel names not found')
                if text.startswith(SCRIPT_IDENTIFIER):
                    text = text.replace(SCRIPT_IDENTIFIER, '').lstrip()
                    answer_type = 'advanced'

                elif text.startswith(TEXT_IDENTIFIER):
                    text = text.replace(TEXT_IDENTIFIER, '').lstrip()
                    answer_type = 'basic'

                sub_answer['text'] = text
                sub_answer['type'] = answer_type
                sub_answer['channel'] = channel
                final_answer_obj.append(sub_answer)

        return final_answer_obj, response_type

    def parse_faqs(self):
        print('parsing FAQs ... ')
        current_ques_obj = None
        result = list()
        for faq_row in self.faq_data:

            current_row = dict(enumerate(faq_row))
            if current_row.get(REF_ID_INDEX, ''):
                current_ques_obj = dict()
                result.append(current_ques_obj)
                current_ques_obj['alternateQuestions'] = list()
                current_ques_obj['alternateAnswers'] = list()
                current_ques_obj['question'] = current_row.get(PRIMARY_QUES_COL_NO, '')
                node_path = current_row.get(2, '')
                tag_path = current_row.get(5, '')
                ref_id = current_row.get(REF_ID_INDEX)
                terms, flatten_terms = self.get_json_format_paths(node_path)
                tags, flatten_tags = self.get_json_format_paths(tag_path)
                terms_with_traits = self.apply_traits_to_path_terms(terms, flatten_terms)
                tags_with_traits = self.apply_traits_to_path_tags(tags, flatten_tags, ref_id)
                answer, response_type = self.parse_answer(faq_row[ANS_COL_NO:])
                if response_type == 'dialog':
                    current_ques_obj['dialogRefId'] = answer
                else:
                    current_ques_obj['answer'] = answer

                current_ques_obj['responseType'] = response_type
                current_ques_obj['terms'] = terms_with_traits[::-1]
                current_ques_obj['tags'] = tags_with_traits[::-1]
                current_ques_obj['refId'] = ref_id

            else:
                alt_question = current_row.get(ALT_QUES_COL_NO, '')
                if alt_question:
                    alt_ques_obj = dict()
                    ref_id = current_row.get(REF_ID_INDEX, '')
                    alt_ques_obj['terms'] = current_ques_obj['terms']
                    alt_ques_obj['question'] = alt_question
                    tag_path = current_row.get(5, '')
                    tags, flatten_tags = self.get_json_format_paths(tag_path)
                    tags_with_traits = self.apply_traits_to_path_tags(tags, flatten_tags, ref_id)
                    alt_ques_obj['tags'] = tags_with_traits[::-1]
                    current_ques_obj['alternateQuestions'].append(alt_ques_obj)
                elif current_row.get(2, ''):
                    node_path = current_row.get(2, '')
                    terms, flatten_terms = self.get_json_format_paths(node_path)
                    terms_with_traits = self.apply_traits_to_path_terms(terms, flatten_terms)
                    self.unmapped_paths.append(terms_with_traits[::-1])

                answer_content = faq_row[ANS_COL_NO:]
                answer_content = list((tuple(dropwhile(lambda t: t is '', answer_content))))
                if answer_content:
                    answer, response_type = self.parse_answer(answer_content)
                    current_ques_obj['alternateAnswers'].append(answer)

        return result

    def parse_global_syn(self):
        print('parsing global synonyms ...')
        result = dict()
        for row in self.global_syn_data:
            current_row = dict(enumerate(row))
            phrase = current_row.get(2)
            if phrase:
                synonyms = current_row.get(3).split(DEFAULT_DELIMITER)
                result[phrase] = synonyms
        return result

    def parse_kg_params(self):
        print('parsing stopwords ...')
        result = dict()
        if self.kg_param_data:
            csv_row = dict(enumerate(self.kg_param_data[0]))
            result = dict()
            lang_code = csv_row.get(2, None)
            stopwords = csv_row.get(3, None)
            result['lang'] = lang_code
            result['stopWords'] = stopwords.split(DEFAULT_DELIMITER) if stopwords else None  # json requirement as none
        return result

    def parse_unmapped_path(self):
        print('parse unmapped paths')
        result = list()
        for path in self.unmapped_paths:
            path_obj = dict()
            path_obj['terms'] = path
            path_obj['preConditions'] = list()
            path_obj['contextTags'] = list()
            result.append(path_obj)
        return result

    def write_json_file(self, file_content, file_path):
        with open(file_path, 'w') as fp:
            json.dump(file_content, fp, indent=2)
        return True

    def parse(self, input_file_path, output_file_path):
        json_export = dict()
        csv_data = self.read_csv_file(input_file_path)
        self.group_csv_data(csv_data)
        node_payload, tag_payload = self.parse_nodes()
        synonym_payload = self.parse_global_syn()
        kg_param_payload = self.parse_kg_params()
        faq_payload = self.parse_faqs()
        unmapped_path = self.parse_unmapped_path()
        json_export['faqs'] = faq_payload
        json_export['synonyms'] = synonym_payload
        json_export['kgParams'] = kg_param_payload
        json_export['nodes'] = node_payload
        json_export['faqtags'] = tag_payload
        json_export['unmappedpath'] = unmapped_path
        self.write_json_file(json_export, output_file_path)
        print('New json generated with filename KnowledgeGraph_export.json in current working directory')
    # def compare_json(self):
    #     from deepdiff import DeepDiff
    #     with open('a.json', 'r') as fp:
    #         a = json.load(fp)
    #     with open('b.json', 'r') as fp:
    #         b = json.load(fp)
    #     diff = DeepDiff(b, a, ignore_order=True, report_repetition=True)
    #     with open('diff.json', 'w') as fp:
    #         json.dump(json.dumps(diff), fp, indent=2)


if __name__ == '__main__':
    file_path = '/home/satyaaditya/work/kore/FAQBot/kg_export/export.csv'
    parser = CsvToJson()
    parser.parse(file_path, 'faq.json')
    # parser.compare_json()
