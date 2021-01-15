import os
import sys
import argparse
import uuid
import copy
import math
import json
import traceback
import re
import datetime
import csv
import itertools

from anytree import Node, PreOrderIter
sys.path.append(str(os.getcwd()))
from analyzer.kg_export.config.config import ontology_analyzer as conf
from analyzer.kg_export.config.config import SYNONYM_DELIMITER, TRAIT_DELIMITER
from log.Logger import Logger
from analyzer.kg_export.language.StopWords import StopWords
from analyzer.kg_export.language.Lemmatize import Lemmatizer
from analyzer.kg_export.language.StringProcessor import StringProcessor

oa_logger = Logger()
string_processor = StringProcessor()
NODE_ID = 0
NODE_NAME = 1
SYNONYMS = 2
HAS_FAQS = 3
IS_MANDATORY = 4
ALLOWED_CHECKS = {
    'unreachable_questions': 'UnreachableQuestions',
    'questions_at_root': 'QuestionsAtRoot',
    'longest_identical_subtree_cousins':'longest_identical_subtree_cousins',
    'leaves_without_faqs':'leaves_without_faqs',
    'chains_of_nodes':'chains_of_nodes',
    'repeated_node_names':'repeated_node_names',
    #'tree_too_long':'tree_too_long',
    #'better_matched_paths':'better_matched_paths',
    'overlapping_alternate_questions':'overlapping_alternate_questions',
    'questions_with_multiple_matched_paths':'questions_with_multiple_matched_paths',
    'possible_new_nodes':'possible_new_nodes'
}


class OntologyAnalyzer:

    def __init__(self):
        self.lemmatizer = Lemmatizer()
        self.stopwords = []
        self.limits = {
            'unreachable_questions_limit': conf.get("UNREACHABLE_QUESTIONS_LIMIT"),
            'questions_at_root_threshold': conf.get('NUMBER_OF_QUESTIONS_AT_ROOT_THRESHOLD'),
            'questions_at_root_limit': conf.get("QUESTIONS_AT_ROOT_LIMIT")
        }

    def parse_term(self, raw_term, global_synonyms={}):
        current_node = copy.deepcopy(raw_term)
        current_node = current_node.strip()
        synonym_set = lambda synonym_list: list(set(synonym_list))

        current_node, _ = current_node.split(TRAIT_DELIMITER) if TRAIT_DELIMITER in current_node else [current_node, '']
        current_node = current_node.split(SYNONYM_DELIMITER)
        current_node, synonyms = current_node[0], current_node[1:]

        if current_node.startswith("**"):
            term = current_node.replace("**", "")
            global_term_synonym = global_synonyms.get(term, [])
            return current_node, term, synonym_set(synonyms + global_term_synonym), "mandatory"
        elif current_node.startswith("!!"):
            term = current_node.replace("!!", "")
            global_term_synonym = global_synonyms.get(term, [])
            return current_node, term, synonym_set(synonyms + global_term_synonym), "organizer"
        else:
            global_term_synonym = global_synonyms.get(current_node, [])
            return current_node, current_node, synonym_set(synonyms + global_term_synonym), "default"

    def valid_root(self):
        root_nodes = {faq["terms"][-1] for faq in self.file_data['faqs'] if faq["terms"]}
        return [root_nodes.pop(), True] if len(root_nodes) == 1 else ["Auntology", False]

    def build_tree(self):
        if not self.file_data['faqs']:
            return None

        path_node_id_map = {}
        node_at_node_map = {}

        # if root node missing in terms
        root_name, is_valid_root = self.valid_root()
        global_synonyms = self.file_data['synonyms'] if 'synonyms' in self.file_data else {}
        root_raw_term, root_term, root_synonyms, root_term_usage = self.parse_term(root_name, global_synonyms)
        root_node_id = uuid.uuid4()
        root = Node((root_node_id, root_term, root_synonyms, True, root_term_usage))
        node_at_node_map[root_term] = root
        unmapped_paths = self.file_data['unmappedpath'] if 'unmappedpath' in self.file_data else []
        for faq_entry in self.file_data['faqs'] + unmapped_paths:
            raw_terms = []
            faq_entry["terms"] = faq_entry["terms"] + [root_name] if not is_valid_root else faq_entry["terms"]
            for idx, raw_term in enumerate(reversed(faq_entry["terms"])):
                raw_term, term, synonyms, term_usage = self.parse_term(raw_term, global_synonyms)
                raw_terms.append(raw_term)
                if idx != 0:
                    terms_path = '/'.join(raw_terms)
                    parent_path = "/".join(raw_terms[0:-1])
                    if terms_path in path_node_id_map:
                        faq_entry['nodeId'] = path_node_id_map[terms_path]
                    else:
                        node_id = uuid.uuid4()
                        faq_entry['nodeId'] = node_id
                        path_node_id_map[terms_path] = node_id
                        has_faq = True if 'question' in faq_entry else False
                        node_at_node_map[terms_path] = Node((node_id, term, synonyms, has_faq, term_usage),
                                                            parent=node_at_node_map[parent_path])
                elif idx == 0:
                    faq_entry['nodeId'] = root_node_id
        # for pre, fill, node in RenderTree(root):
        #     print("%s%s" % (pre, node.name))
        return root

    def lemmatize_and_remove_stopwords(self, text):
        text_wo_punctuation = re.sub(r"[-,.;@#?!&$/]+\ *", " ", text).lower()
        word_tokens = string_processor.normalize(text_wo_punctuation, self.language)
        filtered_sentence = [w for w in word_tokens if not w in self.stopwords]
        return filtered_sentence

    def get_path_array(self, node):
        path = node.path
        path_arr = list()
        for node in path:
            path_arr.append(node.name[NODE_NAME])
        return path_arr

    def create_response(self, paths=[], questions=[], tags=[]):
        response = dict()
        response['paths'] = paths
        response['questions'] = questions
        response['tags'] = tags
        return response

    def check_across_levels(self, leaf, siblingless_nodes, parent_faq_map):
        leaf_path = leaf.path
        requirements_satisfied = True
        for node in leaf_path:
            node_id = node.name[NODE_ID]
            if node != leaf and (node.parent is not None and node.children is not None \
                                 and (node.name[NODE_ID] in parent_faq_map or len(node.children) > 1)):
                requirements_satisfied = False
                break
        return requirements_satisfied

    def check_questions_at_root(self, root_node, parent_faq_map, parent_tags_map):
        faulty_questions = list()
        faulty_tags = list()
        count = 0
        if root_node.name[NODE_ID] in parent_faq_map:
            ques_at_root = parent_faq_map[root_node.name[NODE_ID]]
            tags_at_root = parent_tags_map[root_node.name[NODE_ID]]
            for idx, q in enumerate(ques_at_root):
                for ques_index in range(len(ques_at_root[idx])):
                    if not tags_at_root[idx][ques_index]:
                        faulty_questions.append(q[ques_index])
                        faulty_tags.append(tags_at_root[idx][ques_index])

        return self.create_response(questions=faulty_questions, tags=faulty_tags), True if len(
            faulty_questions) > 0 else False

    def check_path_coverage(self, combined_ngrams, total_content_set, root_node, path_length):
        path_content_set = total_content_set - {''}
        if path_content_set:
            nodes_matched_in_path = [path_node for path_node in path_content_set if path_node in combined_ngrams]
            path_match_percentage = math.ceil((len(nodes_matched_in_path) / path_length) * 100)
            if path_match_percentage >= self.threshold:
                return True
            return False
        return True

    def check_unreachable_questions(self, root_node, parent_faq_map, parent_tags_map):
        faulty_questions = list()
        faulty_nodes = list()
        faulty_tags = list()
        count = 0
        for leaf in self.tree_traversal:
            if leaf.name[NODE_ID] not in parent_faq_map:# or leaf == root_node:
                continue
            path = leaf.path
            total_content_set_initial = set()
            path_set = set()
            for node_index, node_in_path in enumerate(path):
                if node_in_path is not None and node_in_path.name[IS_MANDATORY] != "organizer":
                    if node_index != 0:  # skip root_node name to decide path_coverage
                        node_name = " ".join(self.lemmatize_and_remove_stopwords(node_in_path.name[NODE_NAME]))
                        total_content_set_initial.add(node_name)
                        path_set.add(node_name)
                    for synonym in node_in_path.name[SYNONYMS]:
                        total_content_set_initial.add(" ".join(self.lemmatize_and_remove_stopwords(synonym)))
            if leaf.name[NODE_ID] in parent_faq_map:
                all_questions = parent_faq_map.get(leaf.name[NODE_ID])
                all_tags = parent_tags_map.get(leaf.name[NODE_ID])
                for questions_id in range(0, len(all_questions)):
                    questions = all_questions[questions_id]
                    tags = all_tags[questions_id]
                    for question_id in range(0, len(questions)):
                        question_tags = tags[question_id]
                        tags_norm = [" ".join(self.lemmatize_and_remove_stopwords(tag)) for tag in question_tags]
                        tags_norm = [tag_norm for tag_norm in tags_norm if tag_norm not in ["", " "]]
                        total_path_set = path_set | set(tags_norm)
                        total_content_set = total_content_set_initial | set(tags_norm)
                        question = questions[question_id]
                        unigrams = self.lemmatize_and_remove_stopwords(question)
                        question_norm = " ".join(unigrams)
                        bigrams = self.generate_ngrams(question_norm, 2)
                        trigrams = self.generate_ngrams(question_norm, 3)
                        quadgrams = self.generate_ngrams(question_norm, 4)
                        combined_ngrams = unigrams + bigrams + trigrams + quadgrams

                        path_coverage_match = self.check_path_coverage(combined_ngrams, total_content_set, root_node,
                                                                       len(total_path_set))
                        if not path_coverage_match:
                            count += 1
                            faulty_nodes.append(self.get_path_array(leaf))
                            faulty_questions.append(question)
                            faulty_tags.append(question_tags)
        return self.create_response(faulty_nodes, faulty_questions, faulty_tags), True if len(
            faulty_questions) > 0 else False

    def is_subpath(self, path, longer_path):
        for i in range(1 + len(longer_path) - len(path)):
            if path == longer_path[i:i + len(path)]:
                return True
        return False

    def path_is_not_subset(self, path, matches):
        for matched_path in matches:
            if len(matched_path) > len(path) and self.is_subpath(path, matched_path):
                return False
            if len(matched_path) < len(path) and self.is_subpath(matched_path, path):
                return False
        return True

    def generate_ngrams(self, s, n):
        s = s.lower()
        #        s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
        tokens = [token for token in s.split(" ") if token != ""]
        ngrams = zip(*[tokens[i:] for i in range(n)])
        return [" ".join(ngram) for ngram in ngrams]

    def fetch_ontology(self):
        parent_faq_map = dict()
        parent_tags_map = dict()
        root = self.build_tree()
        for faq_entry in self.file_data['faqs']:

            all_tags = list()
            all_questions = list()

            questions = [faq_entry.get("question")]
            tags = []

            tags_tmp = faq_entry.get('tags')
            tags.append(list({self.parse_term(tag['name'] if isinstance(tag, dict) else tag)[1] for tag in tags_tmp}))

            alternate_questions = faq_entry.get('alternateQuestions')

            for question in alternate_questions:
                if question.get('question').startswith("||"):
                    continue
                questions += [question.get('question')]
                tags_tmp = question.get('tags')
                tags.append(
                    list({self.parse_term(tag['name'] if isinstance(tag, dict) else tag)[1] for tag in tags_tmp}))

            tags = list(tags)

            if faq_entry.get("nodeId", '') in parent_faq_map:
                all_tags = parent_tags_map.get(faq_entry.get('nodeId'))
                all_questions = parent_faq_map.get(faq_entry.get('nodeId'))

            all_tags.append(tags)
            all_questions.append(questions)

            parent_tags_map[faq_entry.get('nodeId')] = all_tags
            parent_faq_map[faq_entry.get("nodeId")] = all_questions

        return root, parent_faq_map, parent_tags_map

    def read_file(self):
        with open(self.file_path) as json_file:
            data = json.load(json_file)
        self.file_data = data

    def generate_csv_report(self, data, file_path):
        header = []
        if not os.path.exists(file_path):
            header = ['error_type', 'question', 'path', 'tags']
        csv_result = []
        for error_type in ALLOWED_CHECKS:
            result_obj = data.get(error_type, {}).get('result', {})
            ques_array = result_obj.get('questions', [])
            paths = result_obj.get('paths', [])
            tags = result_obj.get('tags', [])
            if error_type=="possible_new_nodes":
              for ques_index in range(len(ques_array)):
                    temp=[]
                    temp.extend(paths[ques_index][0])
                    temp.extend(paths[ques_index][1:])
                    

                    path_str = ','.join(temp) if paths else ''
                    question = ques_array[ques_index]
                    tag_str = ','.join(tags[ques_index])
                    csv_result.append([ALLOWED_CHECKS[error_type], question, path_str, tag_str])
            elif error_type=="questions_with_multiple_matched_paths":
                for ques_index in range(len(ques_array)):
                    temp=[]
                
                    for matched_paths in paths[ques_index]["matches"]:

                        temp.append("[matches]-->")
                        temp.extend(matched_paths)

                    #temp.extend(paths[ques_index][0])
                    temp.append("[current path]->")
                    temp.extend(paths[ques_index]["current_path"])
                    

                    path_str = ','.join(temp) if paths else ''
                    question = ques_array[ques_index]
                    tag_str = ','.join(tags[ques_index])
                    csv_result.append([ALLOWED_CHECKS[error_type], question, path_str, tag_str])
                
            else:
                for ques_index in range(len(ques_array)):
                    path_str = ','.join(paths[ques_index]) if paths else ''
                    question = ques_array[ques_index]
                    tag_str = ','.join(tags[ques_index])
                    csv_result.append([ALLOWED_CHECKS[error_type], question, path_str, tag_str])


            with open(file_path, 'w') as fp:
                writer = csv.writer(fp)
                if header:
                    writer.writerow(header)
                #first_row = [data.get('timestamp', ''), data.get('language', '')]
                #writer.writerow(first_row)
                for row in csv_result:
                    writer.writerow(row)

    def write_file(self, data, file_path):
        with open(file_path, 'w') as f:
            json.dump(data, f)

    
    
    def run_diagnostics(self, args):
        self.file_path = args['input_file_path']
        self.language = args['language']
        self.read_file()
        if not self.file_data:
            oa_logger.error("Ontology not present in input file")
            return
        self.threshold = conf.get("PATH_COVERAGE")
        self.stopwords = StopWords.get_stop_words(self.file_data, self.language)
        try:
            self.lemmatizer.set_language(self.language)
            oa_logger.info('Ontology analyzer started')
            root_node, parent_faq_map, parent_tags_map = self.fetch_ontology()

            return root_node, parent_faq_map, parent_tags_map 

            # print("root ",root_node)
            # print("parent_Faq ",parent_faq_map)
            # print("parent_tags_map ",parent_tags_map)
            quit()

            self.tree_traversal = [node for node in PreOrderIter(root_node)]
            response = dict()
            timestamp = datetime.datetime.utcnow().isoformat() + 'Z'

            response['timestamp'] = timestamp
            response['language'] = self.language

            suggestions = 0
            errors = 0
            warnings = 0

            result, present_or_not = self.check_unreachable_questions(root_node, parent_faq_map, parent_tags_map)
            response['unreachable_questions'] = {'result': result, 'type': 'error'}
            errors += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 1 (unreachable_questions) done for bot:' + root_node.name[
                NODE_NAME] + ' and issue present: ' + str(present_or_not))

            result, present_or_not = self.check_questions_at_root(root_node, parent_faq_map, parent_tags_map)
            response['questions_at_root'] = {'result': result, 'type': 'suggestion'}
            suggestions += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 2 (questions_at_root) done for bot:' + root_node.name[
                NODE_NAME] + ' and issue present: ' + str(present_or_not))

            response['no_of_suggestions'] = suggestions
            response['no_of_errors'] = errors
            response['no_of_warnings'] = warnings

            response['total_no_of_issues'] = suggestions + errors + warnings

            oa_logger.info('Ontology analyzer ran for bot:' + root_node.name[NODE_NAME])
            # oa_logger.debug('Ontology analyzer response for bot:' + root_node.name[NODE_NAME] + ' : ' + str(response))
            self.generate_csv_report(response, 'analyzer_report.csv')
            print('Report generated and saved in analyzer_report.csv file ...')
        except Exception as e:
            oa_logger.debug(e)
            traceback.print_exc()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', help='path for input json file', required=True)
    parser.add_argument('--language', help='language of Ontology', default='en')
    _input_arguments = parser.parse_args()

    args = dict()
    args['input_file_path'] =_input_arguments.file_path
    args['language'] =_input_arguments.language
    oa = OntologyAnalyzer()
    oa.run_diagnostics(args)

