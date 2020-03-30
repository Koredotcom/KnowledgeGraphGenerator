import sys
import os

sys.path.append(str(os.getcwd()))

import filetype
import argparse
import uuid
import copy
import math
import json
import traceback
import re
import logging
import datetime
import requests

from anytree import Node, RenderTree, PreOrderIter
from anytree.util import commonancestors
from textblob import TextBlob

from kg_export.config.config import ontology_analyzer as conf
from kg_export.config.config import SYNONYM_DELIMITER, TRAIT_DELIMITER, NODE_IDENTIFIERS
from kg_export.log.Logger import Logger
from kg_export.language.StopWords import StopWords
from kg_export.language.Lemmatize import Lemmatizer
from kg_export.language.StringProcessor import StringProcessor

oa_logger = Logger('ont_analyzer')
string_processor = StringProcessor()

NODE_ID = 0
NODE_NAME = 1
SYNONYMS = 2
HAS_FAQS = 3
IS_MANDATORY = 4


class OntologyAnalyzer:

    def __init__(self):
        self.lemmatizer = Lemmatizer()
        self.stopwords = []
        self.limits = {
            'leaves_without_faqs_limit': conf.get("LEAVES_WITHOUT_FAQS_LIMIT"),
            'chains_of_nodes_limit': conf.get("CHAINS_OF_NODES_LIMIT"),
            'duplicate_sibling_nodes_limit': conf.get("DUPLICATE_SIBLING_NODES_LIMIT"),
            'unreachable_questions_limit': conf.get("UNREACHABLE_QUESTIONS_LIMIT"),
            'better_matched_paths_limit': conf.get("BETTER_MATCHED_PATHS_LIMIT"),
            'overlapping_alternate_questions_limit': conf.get("OVERLAPPING_ALTERNATE_QUESTIONS_LIMIT"),
            'questions_with_multiple_matched_paths_limit': conf.get("QUESTIONS_WITH_MULTIPLE_MATCHED_PATHS_LIMIT"),
            'possible_new_nodes_limit': conf.get("POSSIBLE_NEW_NODES_LIMIT"),
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

    def longest_repeated_substring(self, input):
        len_of_input = len(input)
        LCSRe = [[0 for x in range(len_of_input + 1)]
                 for y in range(len_of_input + 1)]

        res = list()
        res_length = 0

        index = 0
        for i in range(1, len_of_input + 1):
            for j in range(i + 1, len_of_input + 1):
                # (j-i) > LCSRe[i-1][j-1] to remove
                # overlapping
                if (input[i - 1].name[NODE_NAME] == input[j - 1].name[NODE_NAME] and
                        LCSRe[i - 1][j - 1] < (j - i)):
                    LCSRe[i][j] = LCSRe[i - 1][j - 1] + 1

                    if (LCSRe[i][j] > res_length):
                        res_length = LCSRe[i][j]
                        index = max(i, index)
                else:
                    LCSRe[i][j] = 0

        if (res_length > 0):
            for i in range(index - res_length + 1,
                           index + 1):
                node_label = input[i - 1].name[NODE_NAME]
                for node in input:
                    if node_label == node.name[NODE_NAME]:
                        #            res = res + input[i - 1][1]
                        res.append(node)
        return res

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

    def check_for_identical_subtree_cousins(self, root_node):
        longest_repeating_nodes = self.longest_repeated_substring(self.tree_traversal)
        if longest_repeating_nodes == list():
            return self.create_response(), False
        node_1 = longest_repeating_nodes[0]
        node_2 = longest_repeating_nodes[1]
        common_ancestors = commonancestors(node_1, node_2)
        if len(common_ancestors) > 0:
            lowest_common_ancestor = common_ancestors[-1]
            node_1_ht = len(node_1.path)
            node_2_ht = len(node_2.path)
            offset_ht = len(lowest_common_ancestor.path)
            if offset_ht > 1 and node_1_ht - offset_ht == node_2_ht - offset_ht:
                path_1_arr = self.get_path_array(node_1)
                path_2_arr = self.get_path_array(node_2)

                return self.create_response([path_1_arr, path_2_arr], list(), list()), True
            else:
                return self.create_response(), False
        else:
            return self.create_response(), False

    def check_for_leaves_without_FAQs(self, root_node):
        count = 0
        leaves = root_node.leaves
        faulty_leaves = list()
        for leaf in leaves:
            if (leaf.name[HAS_FAQS]) == False:
                count += 1
                faulty_leaves.append(self.get_path_array(leaf))
                if count == self.limits.get('leaves_without_faqs_limit'):
                    return self.create_response(faulty_leaves, list(), list()), True if len(
                        faulty_leaves) > 0 else False
        return self.create_response(paths=faulty_leaves), True if len(faulty_leaves) > 0 else False

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

    def check_for_chains_of_nodes(self, root_node, parent_faq_map, parent_tags_map):
        siblingless_nodes = set()
        faulty_nodes = list()
        faulty_questions = list()
        faulty_tags = list()
        count = 0
        for node in self.tree_traversal:
            if len(node.siblings) == 0:
                siblingless_nodes.add(node.name[NODE_ID])

        leaves = root_node.leaves
        for leaf_node in leaves:
            if leaf_node.name[NODE_ID] in parent_faq_map and (
                    len(leaf_node.path) > 2 and self.check_across_levels(leaf_node, siblingless_nodes, parent_faq_map)):
                count += 1
                faulty_nodes.append(self.get_path_array(leaf_node))
                all_questions = parent_faq_map[leaf_node.name[NODE_ID]]
                first_primary_question = all_questions[0][0]
                faulty_questions.append(first_primary_question)
                faulty_tags.append(parent_tags_map[leaf_node.name[NODE_ID]][0][0])
                if count == self.limits.get('chains_of_nodes_limit'):
                    return self.create_response(paths=faulty_nodes, questions=faulty_questions,
                                                tags=faulty_tags), True if len(faulty_nodes) > 0 else False

        return self.create_response(paths=faulty_nodes, questions=faulty_questions, tags=faulty_tags), True if len(
            faulty_nodes) > 0 else False

    def check_questions_at_root(self, root_node, parent_faq_map, parent_tags_map):
        faulty_questions = list()
        faulty_tags = list()
        count = 0
        if root_node.name[NODE_ID] in parent_faq_map:
            ques_at_root = parent_faq_map[root_node.name[NODE_ID]]
            tags_at_root = parent_tags_map[root_node.name[NODE_ID]]
            if len(ques_at_root) > self.limits.get('questions_at_root_threshold'):
                for idx, q in enumerate(ques_at_root):
                    if count <= self.limits.get('questions_at_root_limit'):
                        count += 1
                        faulty_questions.append(q[0])
                        faulty_tags.append(tags_at_root[idx][0])
        return self.create_response(questions=faulty_questions, tags=faulty_tags), True if len(
            faulty_questions) > 0 else False

    def check_for_duplicate_sibling_nodes(self, root_node):
        faulty_nodes = list()
        nodes_considered = set()
        count = 0
        for node in self.tree_traversal:
            parent = node.parent
            if parent is None:
                continue
            siblings = parent.children
            for sibling in siblings:
                if node != sibling and node.name[NODE_NAME] == sibling.name[
                    NODE_NAME] and parent not in nodes_considered:
                    nodes_considered.add(parent)
                    count += 1
                    faulty_nodes.append(self.get_path_array(node))
                    if count == self.limits.get('duplicate_sibling_nodes_limit'):
                        faulty_nodes = faulty_nodes
                        return self.create_response(paths=faulty_nodes), True if len(faulty_nodes) > 0 else False
                    break
        return self.create_response(paths=faulty_nodes), True if len(faulty_nodes) > 0 else False

    def check_if_tree_is_too_long(self, root_node):
        height = root_node.height
        no_of_nodes = len(self.tree_traversal)
        max_permissible_height = math.ceil(math.log2(no_of_nodes))
        if max_permissible_height < height:
            deepest_node = None
            longest_path_list = list()
            for node in self.tree_traversal:
                if node.depth == height:
                    deepest_node = node
                    break
            if deepest_node is None:
                longest_path_list = [self.get_path_array(deepest_node)]
            return self.create_response(paths=longest_path_list), True if len(longest_path_list) > 0 else False
        else:
            return self.create_response(), False

    def check_path_coverage(self, combined_ngrams, total_content_set, root_node, path_length, mandatory_nodes_in_path):
        path_content_set = total_content_set - {''}
        nodes_matched_in_path = [path_node for path_node in path_content_set if path_node in combined_ngrams]
        path_match_percentage = math.ceil((len(nodes_matched_in_path) / path_length) * 100)
        for mandatory_node in mandatory_nodes_in_path:
            mandatory_node_name = mandatory_node.name[NODE_NAME]
            if mandatory_node_name not in combined_ngrams:
                return False
        if path_match_percentage >= self.threshold:
            return True
        return False

    def check_unreachable_questions(self, root_node, parent_faq_map, parent_tags_map):
        faulty_questions = list()
        faulty_nodes = list()
        faulty_tags = list()
        count = 0
        for leaf in self.tree_traversal:
            if leaf.name[NODE_ID] not in parent_faq_map:
                continue
            path = leaf.path
            total_content_set_initial = set()
            path_set = set()
            mandatory_nodes_in_path = set()
            for node_index, node_in_path in enumerate(path):
                if node_in_path is not None and node_in_path.name[IS_MANDATORY] == "mandatory":
                    mandatory_nodes_in_path.add(node_in_path)


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
                        if len(total_content_set) == 0:
                            path_coverage_match = 1
                        else:
                            path_coverage_match = self.check_path_coverage(combined_ngrams, total_content_set, root_node,
                                                                       len(total_path_set), mandatory_nodes_in_path)
                        if not path_coverage_match:
                            count += 1
                            faulty_nodes.append(self.get_path_array(leaf))
                            faulty_questions.append(question)
                            faulty_tags.append(question_tags)
        return self.create_response(faulty_nodes, faulty_questions, faulty_tags), True if len(
            faulty_questions) > 0 else False

    def construct_faulty_overlapping_questions(self, questions_map, questions_paths_map, questions_tag_map):
        faulty_questions = list()
        faulty_nodes = list()
        faulty_tags = list()
        for q in questions_map:
            alt_questions = list()
            for ques in questions_map[q]:
                if ques != q:
                    alt_questions.append(ques)
            question_obj = {'alternate': alt_questions}
            if q in questions_map[q]:
                question_obj['primary'] = q
            faulty_questions.append(question_obj)
            faulty_nodes.append(questions_paths_map[q])
            faulty_tags.append(questions_tag_map[q])
        return faulty_nodes, faulty_questions, faulty_tags

    def check_overlapping_alternate_questions(self, parent_faq_map):
        count = 0
        questions_map = dict()
        questions_tag_map = dict()
        questions_paths_map = dict()
        for parent in parent_faq_map:
            all_questions = parent_faq_map.get(parent)
            for questions_id, questions in enumerate(all_questions):
                for question_id, question in enumerate(questions):
                    question_set = set(self.lemmatize_and_remove_stopwords(question))
                    for q in questions:
                        if q != question:
                            q_set = set(self.lemmatize_and_remove_stopwords(q))
                            ques_len = len(question_set)
                            if 10 * len(q_set & question_set) > 9 * len(question_set) and 10 * len(
                                    q_set & question_set) > 9 * len(q_set):
                                count += 1
                                parent_path = list()
                                for node in self.tree_traversal:
                                    if node.name[NODE_ID] == parent:
                                        parent_path = self.get_path_array(node)
                                #                                faulty_questions.append((questions[0], question, q))
                                if questions[0] in questions_map:
                                    overlapping_qs = list(questions_map[questions[0]])
                                    questions_map[questions[0]] = set(overlapping_qs + [question, q])
                                else:
                                    questions_map[questions[0]] = set([question, q])
                                    questions_paths_map[questions[0]] = parent_path
                                    questions_tag_map[questions[0]] = []
                                #                                faulty_nodes.append(parent_path)
                                if count == self.limits.get('overlapping_alternate_questions_limit'):
                                    faulty_nodes, faulty_questions, faulty_tags = self.construct_faulty_overlapping_questions(
                                        questions_map, questions_paths_map, questions_tag_map)
                                    return self.create_response(faulty_nodes, faulty_questions,
                                                                faulty_tags), True if len(
                                        faulty_questions) > 0 else False
        faulty_nodes, faulty_questions, faulty_tags = self.construct_faulty_overlapping_questions(questions_map,
                                                                                                  questions_paths_map,
                                                                                                  questions_tag_map)
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

    def path_match(self, paths, utterance, root, mandatory):
        matches = list()
        max_no_of_paths = conf.get('NUMBER_OF_MULTIPLE_PATH_MATCHES')
        count = 1
        for idx, path in enumerate(paths):
            utterance_set = set(self.lemmatize_and_remove_stopwords(utterance))
            mandatory_nodes = set(mandatory[idx])
            match = False
            if mandatory_nodes:
                if mandatory_nodes.issubset(utterance_set):
                    match = True
            else:
                if 2 * len(set([p.lower() for p in path]) & utterance_set) >= len(path):
                    match = True
            if match:
                path = [root] + path
                if self.path_is_not_subset(path, matches):
                    matches.append(path)
                count += 1
                if count > max_no_of_paths:
                    return matches
        return matches

    def check_number_of_matched_paths_per_question(self, root_node, parent_faq_map, parent_tags_map):
        faq_nodes = list()
        faulty_nodes = list()
        faulty_questions = list()
        faulty_tags = list()
        parent_path_map = dict()

        for node in self.tree_traversal:
            if node.name[NODE_ID] in parent_faq_map:
                faq_nodes.append(node)
                parent_path_map[node.name[NODE_ID]] = self.get_path_array(node)
        paths = list()
        mandatory_in_path = list()
        count = 0
        questions_with_multiple_paths = dict()
        for faq_node in faq_nodes:
            new_path = list()
            mandatory_nodes = list()
            path = faq_node.path
            for node in path:
                if node == root_node:
                    continue
                node_name = node.name[NODE_NAME].strip('!!').strip('**')
                new_path.append(node_name)
                if node.name[IS_MANDATORY] == "mandatory":
                    mandatory_nodes.append(node.name[NODE_NAME])
            if new_path != list():
                paths.append(new_path)
                mandatory_in_path.append(mandatory_nodes)

        for parent in parent_faq_map:
            all_questions = parent_faq_map.get(parent)
            all_tags = parent_tags_map.get(parent)
            for questions_id, questions in enumerate(all_questions):
                tags = all_tags[questions_id]
                for question_id, question in enumerate(questions):
                    tag = tags[question_id]
                    matches = self.path_match(paths, question, root_node.name[NODE_NAME], mandatory_in_path)
                    if len(matches) > 1:
                        count += 1
                        current_path = parent_path_map[parent]
                        faulty_nodes.append({'matches': matches, 'current_path': current_path})
                        faulty_questions.append(question)
                        faulty_tags.append(tag)

                        if count == self.limits.get('questions_with_multiple_matched_paths_limit'):
                            return self.create_response(faulty_nodes, faulty_questions, faulty_tags), True if len(
                                faulty_questions) > 0 else False

        return self.create_response(faulty_nodes, faulty_questions, faulty_tags), True if len(
            faulty_questions) > 0 else False

    def remove_noun_phrases(self, question):
        blob = TextBlob(question)
        np = list(blob.noun_phrases)
        new_question = ''
        #        question = question.translate(str.maketrans('', '', string.punctuation))
        question = re.sub(r"[-,.;@#?!&$/]+\ *", " ", question)

        for word in question.split(' '):
            word_present_in_np = False
            for noun_phrase in np:
                if word in set(noun_phrase.split(' ')):
                    word_present_in_np = True
                    break
            if not word_present_in_np:
                new_question = new_question + ' ' + word
        return np, new_question

    def remove_duplicates(self, parent_path, set_diff):
        parent_path = self.lemmatize_and_remove_stopwords(" ".join(parent_path))
        new_diff = list()
        elements_considered = set()
        set_diff_descending = sorted(list(set_diff), key=len, reverse=True)

        for element in set_diff_descending:
            words = self.lemmatize_and_remove_stopwords(element)
            any_word_present = False
            elements_considered_list = list(map(str, elements_considered))
            words_in_elements_considered = " ".join(elements_considered_list)

            for word in words:
                if word in parent_path or word in words_in_elements_considered:
                    any_word_present = True

            if not any_word_present:
                new_diff.append(element)
                elements_considered.add(element)

        return new_diff

    def remove_unnecessary_nodes(self, faulty_nodes):
        cleaned_faulty_nodes = list()
        for faulty_node in faulty_nodes:
            parent_path = faulty_node[0]
            faulty_node_wo_parent = faulty_node[1:]
            if parent_path is not None:
                cleaned_faulty_nodes.append([parent_path] + sorted(faulty_node_wo_parent, key=len, reverse=True)[
                                                            0:conf.get('NODES_TO_RECOMMEND_IN_POSSIBLE_NEW_NODES')])
            else:
                cleaned_faulty_nodes.append(sorted(faulty_node_wo_parent, key=len, reverse=True)[
                                            0:conf.get('NODES_TO_RECOMMEND_IN_POSSIBLE_NEW_NODES')])
        return cleaned_faulty_nodes

    def check_possible_new_nodes(self, root_node, parent_faq_map, parent_tags_map):
        faulty_nodes = list()
        faulty_questions = list()
        faulty_tags = list()
        leaves = [node for node in PreOrderIter(root_node)]
        count = 0
        for parent in parent_faq_map:
            all_questions = parent_faq_map.get(parent)
            all_tags = parent_tags_map.get(parent)
            for questions_id in range(0, len(all_questions)):
                questions = all_questions[questions_id]
                tags = all_tags[questions_id]
                question_lists = list()
                question_question_set_map = dict()
                question_tag_map = dict()
                one_ques = False
                question = questions[0]
                tag = tags[0]
                noun_phrases, question_wo_noun_phrases = self.remove_noun_phrases(question)
                question_list = self.lemmatize_and_remove_stopwords(question_wo_noun_phrases)
                question_list += noun_phrases
                question_lists.append(question_list)

                if not one_ques:
                    question_question_set_map[question] = question_list
                    question_tag_map[question] = tag
                    one_ques = True

                path_terms = set()

                for leaf in leaves:
                    if leaf.name[NODE_ID] == parent:
                        path = leaf.path
                        for node in path:
                            path_terms.add(node.name[NODE_NAME].lower().strip('!!').strip('**'))
                        break

                for question_list in question_lists:
                    question_set_2 = question_lists[0]
                    for qs in question_lists:
                        question_set_2 = set(question_set_2) & set(qs)

                    set_diff = question_set_2 - path_terms - set(tag)
                    if len(set_diff) > len(question_list) * 0.2:
                        for q in question_question_set_map:
                            if question_question_set_map.get(q) == question_list:
                                count += 1
                                #                                questions_with_probable_new_nodes[q] = list(filter(lambda x: len(x) > 0, list(set_diff)))
                                parent_path = list()
                                for leaf in leaves:
                                    if leaf.name[NODE_ID] == parent:
                                        parent_path = self.get_path_array(leaf)
                                diff_wo_duplicates = self.remove_duplicates(parent_path, set_diff)
                                if len(diff_wo_duplicates) > 0:
                                    faulty_questions.append(q)
                                    faulty_tags.append(question_tag_map[q])
                                    faulty_nodes.append(
                                        [parent_path] + list(filter(lambda x: len(x) > 0, list(diff_wo_duplicates))))
                                if count == self.limits.get('possible_new_nodes_limit'):
                                    faulty_nodes = self.remove_unnecessary_nodes(faulty_nodes)
                                    return self.create_response(faulty_nodes, faulty_questions,
                                                                faulty_tags), True if len(
                                        faulty_questions) > 0 else False
                                break
        faulty_nodes = self.remove_unnecessary_nodes(faulty_nodes)
        return self.create_response(faulty_nodes, faulty_questions, faulty_tags), True if len(
            faulty_questions) > 0 else False

    def generate_total_content(self, node):
        path = node.path
        total_content = list()
        synonyms = list()
        for node_in_path in path:
            if node_in_path is not None:
                content = node_in_path.name[NODE_NAME] + ' ' + ' '.join(node_in_path.name[SYNONYMS]) \
                    if node_in_path.name[SYNONYMS] else node_in_path.name[NODE_NAME]
                content = self.lemmatize_and_remove_stopwords(content)
                total_content += content
                synonyms += (node_in_path.name[SYNONYMS])
        return total_content, synonyms

    def find_node_from_id(self, inp_node, tree_traversal):
        for node in tree_traversal:
            if node.name[NODE_ID] == inp_node:
                return node

    def tanimoto(self, question_parts, path_list):
        return float(len(set(question_parts) & set(path_list))) / (len(set(question_parts) | set(path_list)))

    def generate_ngrams(self, s, n):
        s = s.lower()
        #        s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
        tokens = [token for token in s.split(" ") if token != ""]
        ngrams = zip(*[tokens[i:] for i in range(n)])
        return [" ".join(ngram) for ngram in ngrams]

    def normalize_path(self, path):
        path_norm = list()
        for node in path:
            node_norm = " ".join(self.lemmatize_and_remove_stopwords(node))
            path_norm.append(node_norm)
        return path_norm

    def check_if_there_is_a_better_path(self, question, all_paths, path_list):
        question_parts = self.lemmatize_and_remove_stopwords(question)
        question_norm = " ".join(question_parts)
        bigrams = self.generate_ngrams(question_norm, 2)
        trigrams = self.generate_ngrams(question_norm, 3)
        quadgrams = self.generate_ngrams(question_norm, 4)

        final_question_parts = question_parts + bigrams + trigrams + quadgrams
        given_path_score = self.tanimoto(final_question_parts, self.normalize_path(path_list))

        max_score = copy.deepcopy(given_path_score)
        max_path = None
        for (alt_path, norm_path) in all_paths:
            alt_score = self.tanimoto(final_question_parts, norm_path)
            if alt_score > max_score:
                max_score = alt_score
                max_path = alt_path

        if given_path_score < 0.9 * max_score \
                and max_path is not None and max_score > 0.1:
            return max_path
        else:
            return list()

    def check_for_better_matched_paths(self, root_node, parent_faq_map):
        node_content_map = dict()
        node_synonyms_map = dict()
        count = 0
        better_paths = dict()
        faulty_nodes = list()
        faulty_questions = list()
        faulty_tags = list()
        for node in self.tree_traversal:
            total_content, synonyms = self.generate_total_content(node)
            node_synonyms_map[node] = synonyms
            node_content_map[node] = set(total_content)

        all_paths = list()

        for node in self.tree_traversal:
            path_node_names = list()
            path = node.path
            for path_node in path:
                path_node_names.append(path_node.name[NODE_NAME])
            norm_path = self.normalize_path(path_node_names)
            all_paths.append((path_node_names, norm_path))

        for parent in parent_faq_map:
            if parent != root_node.name[NODE_ID]:
                continue
            all_questions = parent_faq_map.get(parent)
            node = self.find_node_from_id(parent, self.tree_traversal)
            path_to_node = node.path
            path_list = list()
            for path_node in path_to_node:
                path_list.append(path_node.name[NODE_NAME])
            for questions_id, questions in enumerate(all_questions):
                for question_id, question in enumerate(questions):
                    better_path = self.check_if_there_is_a_better_path(question, all_paths, path_list)
                    if len(better_path) > 0:
                        if count < self.limits.get('better_matched_paths_limit'):
                            count += 1
                            faulty_nodes.append(path_list)
                            faulty_questions.append((str(questions[0]), better_path))
                            faulty_tags.append([])
                            better_paths[str([questions[0]] + path_list)] = better_path
                            break
        return self.create_response(faulty_nodes, faulty_questions, faulty_tags), True if len(
            faulty_questions) > 0 else False

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

            if faq_entry.get("nodeId") in parent_faq_map:
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

    def write_file(self, data):
        file_name = self.file_path.split(".")[0].split("/")[-1]
        with open('%sReport.json' % (file_name), 'w') as f:
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
            self.tree_traversal = [node for node in PreOrderIter(root_node)]
            response = dict()
            timestamp = datetime.datetime.utcnow().isoformat() + 'Z'

            response['timestamp'] = timestamp
            response['language'] = self.language

            suggestions = 0
            errors = 0
            warnings = 0

            result, present_or_not = self.check_for_identical_subtree_cousins(root_node)
            response['longest_identical_subtree_cousins'] = {'result': result, 'type': 'suggestion'}
            suggestions += int(present_or_not)
            oa_logger.debug(
                'Ontology analyzer: Check 1 (longest_identical_subtree_cousins) done for bot:' + root_node.name[
                    NODE_NAME] + ' and issue present: ' + str(present_or_not))

            result, present_or_not = self.check_for_leaves_without_FAQs(root_node)
            response['leaves_without_faqs'] = {'result': result, 'type': 'suggestion'}
            suggestions += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 2 (leaves_without_faqs) done forbot:' + root_node.name[
                NODE_NAME] + ' and issue present: ' + str(present_or_not))

            result, present_or_not = self.check_for_chains_of_nodes(root_node, parent_faq_map, parent_tags_map)
            response['chains_of_nodes'] = {'result': result, 'type': 'suggestion'}
            suggestions += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 3 (chains_of_nodes) done for bot:' + root_node.name[
                NODE_NAME] + ' and issue present: ' + str(present_or_not))

            result, present_or_not = self.check_for_duplicate_sibling_nodes(root_node)
            response['repeated_node_names'] = {'result': result, 'type': 'warning'}
            warnings += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 4 (repeated_node_names) done for bot:' + root_node.name[
                NODE_NAME] + ' and issue present: ' + str(present_or_not))

            result, present_or_not = self.check_if_tree_is_too_long(root_node)
            response['tree_too_long'] = {'result': result, 'type': 'warning'}
            warnings += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 5 (tree_too_long) done for bot:' + root_node.name[
                NODE_NAME] + ' and issue present: ' + str(present_or_not))

            result, present_or_not = self.check_unreachable_questions(root_node, parent_faq_map, parent_tags_map)
            response['unreachable_questions'] = {'result': result, 'type': 'error'}
            errors += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 6 (unreachable_questions) done for bot:' + root_node.name[
                NODE_NAME] + ' and issue present: ' + str(present_or_not))

            result, present_or_not = self.check_for_better_matched_paths(root_node, parent_faq_map)
            response['better_matched_paths'] = {'result': result, 'type': 'warning'}
            warnings += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 7 (better_matched_paths) done forbot:' + root_node.name[
                NODE_NAME] + ' and issue present: ' + str(present_or_not))

            result, present_or_not = self.check_overlapping_alternate_questions(parent_faq_map)
            response['overlapping_alternate_questions'] = {'result': result, 'type': 'suggestion'}
            suggestions += int(present_or_not)
            oa_logger.debug(
                'Ontology analyzer: Check 8 (overlapping_alternate_questions) done for bot:' + root_node.name[
                    NODE_NAME] + ' and issue present: ' + str(present_or_not))

            result, present_or_not = self.check_number_of_matched_paths_per_question(root_node, parent_faq_map,
                                                                                     parent_tags_map)
            response['questions_with_multiple_matched_paths'] = {'result': result, 'type': 'warning'}
            warnings += int(present_or_not)
            oa_logger.debug(
                'Ontology analyzer: Check 9 (questions_with_multiple_matched_paths) done for bot:' + root_node.name[
                    NODE_NAME] + ' and issue present: ' + str(present_or_not))

            result, present_or_not = self.check_possible_new_nodes(root_node, parent_faq_map, parent_tags_map)
            response['possible_new_nodes'] = {'result': result, 'type': 'warning'}
            warnings += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 10 (possible_new_nodes) done for bot:' + root_node.name[
                NODE_NAME] + ' and issue present: ' + str(present_or_not))

            result, present_or_not = self.check_questions_at_root(root_node, parent_faq_map, parent_tags_map)
            response['questions_at_root'] = {'result': result, 'type': 'suggestion'}
            suggestions += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 11 (questions_at_root) done for bot:' + root_node.name[
                NODE_NAME] + ' and issue present: ' + str(present_or_not))

            response['no_of_suggestions'] = suggestions
            response['no_of_errors'] = errors
            response['no_of_warnings'] = warnings

            response['total_no_of_issues'] = suggestions + errors + warnings

            oa_logger.info('Ontology analyzer ran for bot:' + root_node.name[NODE_NAME])
            oa_logger.debug('Ontology analyzer response for bot:' + root_node.name[NODE_NAME] + ' : ' + str(response))
            self.write_file(response)
        except Exception as e:
            oa_logger.debug(e)
            traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', help='path for input json file', required=True)
    parser.add_argument('--language', help='language of Ontology', default='en')
    _input_arguments = parser.parse_args()

    args = dict()
    args['input_file_path'] = _input_arguments.file_path
    args['language'] = _input_arguments.language
    oa = OntologyAnalyzer()
    oa.run_diagnostics(args)
