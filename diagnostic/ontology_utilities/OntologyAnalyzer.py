import sys
import os
from anytree import Node, RenderTree, PreOrderIter
sys.path.append(str(os.getcwd()))

# from ontology.DBManager import DBManager
# from ontology_utilities.DBManager import DBManager as OADBManager
from anytree.util import commonancestors
import copy
import math
import json
import traceback
import re
import logging
#from share.config.ConfigManager import ConfigManager
import datetime
#from share.language.StopWords import StopWords
from share.language.Lemmatize import Lemmatizer
import requests
from textblob import TextBlob
from log.Logger import Logger


# config_manager = ConfigManager()
# qna_conf = config_manager.load_config(key='qna')
# conf = config_manager.load_config(key='ontology_analyzer')
# remote_config = config_manager.load_config(key="remote_config")

oa_logger =Logger() #logging.getLogger('ont_analyzer')

NODE_ID = 0
NODE_NAME = 1
SYNONYMS = 2
HAS_FAQS = 3
IS_MANDATORY = 4

class OntologyAnalyzer:

    def __init__(self):
        self.kt_id = None
        self.language = None
        self.doc_id = None
        # self.db_manager = DBManager()
        # self.ont_analyzer_db_manager = OADBManager()
        self.lemmatizer = Lemmatizer()
        self.stopwords = []
        self.limits = {
        'leaves_without_faqs_limit': 10,
        'chains_of_nodes_limit': 10,
        'duplicate_sibling_nodes_limit': 50,
        'unreachable_questions_limit': 10,
        'better_matched_paths_limit': 50,
        'overlapping_alternate_questions_limit': 10,
        'questions_with_multiple_matched_paths_limit': 50,
        'possible_new_nodes_limit': 50,
        'questions_at_root_threshold': 50,
        'questions_at_root_limit': 10
        }

    def build_tree(self, parent_child_map, parent_child_label_map, nodes_with_faq_children, synonym_map, term_usage_map):
        root = parent_child_map.get(None)
        node_at_node_map = dict()
        if len(parent_child_label_map) == 0:
            return root
        at_root = Node((root[0], parent_child_label_map.get(None)[0], synonym_map.get(root[0]) ,root[0] in nodes_with_faq_children, term_usage_map.get(root[0])))
        node_at_node_map[root[0]] = at_root

        nodes_considered = set(root)
        nodes_considered_previously = set()
        new_nodes_added = True
        while (new_nodes_added):
            new_nodes = (nodes_considered - nodes_considered_previously)
            nodes_considered_previously = copy.deepcopy(nodes_considered)
            for node in new_nodes:
                if node not in parent_child_map:
                    continue
                children = parent_child_map.get(node)
                children_label = parent_child_label_map.get(node)

                for child_id in range(0, len(children)):
                    child = children[child_id]
                    child_label = children_label[child_id]
                    nodes_considered.add(child)
                    at_child = Node((child, child_label, synonym_map.get(child), child in nodes_with_faq_children, term_usage_map.get(child)), parent=node_at_node_map.get(node))
                    node_at_node_map[child] = at_child
            if len(nodes_considered) > len(nodes_considered_previously):
                new_nodes_added = True
            else:
                new_nodes_added = False
        return at_root


    def lemmatize_and_remove_stopwords(self, text):
        
        text_wo_punctuation = re.sub(r"[-,.;@#?!&$/]+\ *", " ", text).lower()
        word_tokens = self.lemmatizer.lemmatize(text_wo_punctuation)
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
                    return self.create_response(faulty_leaves, list(), list()), True if len(faulty_leaves) > 0 else False
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
            if leaf_node.name[NODE_ID] in parent_faq_map and (len(leaf_node.path) > 2 and self.check_across_levels(leaf_node, siblingless_nodes, parent_faq_map)):
                count += 1
                faulty_nodes.append(self.get_path_array(leaf_node))
                all_questions = parent_faq_map[leaf_node.name[NODE_ID]]
                first_primary_question = all_questions[0][0]
                faulty_questions.append(first_primary_question)
                faulty_tags.append(parent_tags_map[leaf_node.name[NODE_ID]][0][0])
                if count == self.limits.get('chains_of_nodes_limit'):
                    return self.create_response(paths=faulty_nodes, questions=faulty_questions, tags=faulty_tags), True if len(faulty_nodes) > 0 else False

        return self.create_response(paths=faulty_nodes, questions=faulty_questions, tags=faulty_tags), True if len(faulty_nodes) > 0 else False

    def check_questions_at_root(self, root_node, parent_faq_map, parent_tags_map):
        faulty_questions = list()
        faulty_tags = list()
        count = 0
        if root_node.name[NODE_ID] in parent_faq_map:
            ques_at_root = parent_faq_map[root_node.name[NODE_ID]]
            tags_at_root = parent_tags_map[root_node.name[NODE_ID]]
            if len(ques_at_root) > self.limits.get('questions_at_root_threshold'):
                for idx, q in enumerate(ques_at_root):
                    if count == self.limits.get('questions_at_root_limit'):
                        count += 1
                        faulty_questions.append(q[0])
                        faulty_tags.append(tags_at_root[idx][0])
        return self.create_response(questions=faulty_questions, tags=faulty_tags), True if len(faulty_questions) > 0 else False

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
                if node != sibling and node.name[NODE_NAME] == sibling.name[NODE_NAME] and parent not in nodes_considered:
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

    def check_path_coverage(self,combined_ngrams,total_content_set,root_node,path_length):
        path_content_set = total_content_set-{''}
        nodes_matched_in_path = [path_node for path_node in path_content_set if path_node in combined_ngrams]
        if path_length != 0:
            path_match_percentage = math.ceil((len(nodes_matched_in_path)/path_length)*100)
        else:
            path_match_percentage = 0
        if path_match_percentage >= self.threshold:
            return True
        return False

    def check_unreachable_questions(self, root_node, parent_faq_map, parent_tags_map):
        faulty_questions = list()
        faulty_nodes = list()
        faulty_tags = list()
        count = 0
        for leaf in self.tree_traversal:
            if leaf.name[NODE_ID] not in parent_faq_map or leaf == root_node:
                continue
            path = leaf.path
            total_content_set_initial = set()
            path_set = set()
            for node_index,node_in_path in enumerate(path):
                if node_in_path is not None and node_in_path.name[IS_MANDATORY]!="organizer":
                    if node_index!=0: #skip root_node name to decide path_coverage
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
                        tags_norm = [tag_norm for tag_norm in tags_norm if tag_norm not in [""," "]]
                        total_path_set = path_set | set(tags_norm)
                        total_content_set = total_content_set_initial | set(tags_norm)
                        question = questions[question_id]
                        unigrams = self.lemmatize_and_remove_stopwords(question)
                        question_norm = " ".join(unigrams)
                        bigrams = self.generate_ngrams(question_norm, 2)
                        trigrams = self.generate_ngrams(question_norm, 3)
                        quadgrams = self.generate_ngrams(question_norm, 4)
                        combined_ngrams = unigrams + bigrams + trigrams + quadgrams

                        path_coverage_match = self.check_path_coverage(combined_ngrams,total_content_set,root_node,len(total_path_set))
                        if not path_coverage_match:
                            count += 1
                            faulty_nodes.append(self.get_path_array(leaf))
                            faulty_questions.append(question)
                            faulty_tags.append(question_tags)
        return self.create_response(faulty_nodes, faulty_questions, faulty_tags), True if len(faulty_questions) > 0 else False

    def construct_faulty_overlapping_questions(self, questions_map, questions_paths_map, questions_tag_map):
        faulty_questions = list()
        faulty_nodes = list()
        faulty_tags = list()
        for q in questions_map:
            alt_questions = list()
            for ques in questions_map[q]:
                if ques != q:
                    alt_questions.append(ques)
            question_obj = {'alternate':alt_questions}
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
            for questions_id,questions in enumerate(all_questions):
                for question_id,question in enumerate(questions):
                    
                    question_set = set(self.lemmatize_and_remove_stopwords(question))
                    for q in questions:
                        if q != question:
                            q_set = set(self.lemmatize_and_remove_stopwords(q))
                            ques_len = len(question_set)
                            if 10 * len(q_set & question_set) > 9 * len(question_set) and 10 * len(q_set & question_set) > 9 * len(q_set):
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
                                    faulty_nodes, faulty_questions, faulty_tags = self.construct_faulty_overlapping_questions(questions_map, questions_paths_map, questions_tag_map)
                                    return self.create_response(faulty_nodes, faulty_questions, faulty_tags), True if len(faulty_questions) > 0 else False
        faulty_nodes, faulty_questions, faulty_tags = self.construct_faulty_overlapping_questions(questions_map, questions_paths_map, questions_tag_map)
        return self.create_response(faulty_nodes, faulty_questions, faulty_tags), True if len(faulty_questions) > 0 else False

    def is_subpath(self, path, longer_path):
        for i in range(1 + len(longer_path) - len(path)):
            if path == longer_path[i:i+len(path)]:
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
        max_no_of_paths = 2#conf.get('NUMBER_OF_MULTIPLE_PATH_MATCHES')
        count = 1
        for idx, path in enumerate(paths):
            utterance_set = set(self.lemmatize_and_remove_stopwords(utterance))
            mandatory_nodes = set(mandatory[idx])
            match = False
            if mandatory_nodes:
                if mandatory_nodes.issubset(utterance_set):
                    match = True
            else:
                if 2*len(set([p.lower() for p in path]) & utterance_set) >= len(path):
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
                for question_id,question in enumerate(questions):
                    tag = tags[question_id]
                    matches = self.path_match(paths, question, root_node.name[NODE_NAME], mandatory_in_path)
                    if len(matches) > 1:
                        count += 1
                        current_path = parent_path_map[parent]
                        faulty_nodes.append({'matches': matches, 'current_path' : current_path})
                        faulty_questions.append(question)
                        faulty_tags.append(tag)

                        if count == self.limits.get('questions_with_multiple_matched_paths_limit'):
                            return self.create_response(faulty_nodes, faulty_questions, faulty_tags), True if len(faulty_questions) > 0 else False

        return self.create_response(faulty_nodes, faulty_questions, faulty_tags), True if len(faulty_questions) > 0 else False

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
                cleaned_faulty_nodes.append([parent_path] + sorted(faulty_node_wo_parent, key=len, reverse=True)[0:2])
            else:
                cleaned_faulty_nodes.append(sorted(faulty_node_wo_parent, key=len, reverse=True)[0:2])
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
            for questions_id in range(0,len(all_questions)):
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
                    if len(set_diff) > len(question_list)*0.2:
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
                                    faulty_nodes.append([parent_path] + list(filter(lambda x: len(x) > 0, list(diff_wo_duplicates))))
                                if count == self.limits.get('possible_new_nodes_limit'):
                                    faulty_nodes = self.remove_unnecessary_nodes(faulty_nodes)
                                    return self.create_response(faulty_nodes, faulty_questions, faulty_tags), True if len(faulty_questions) > 0 else False
                                break
        faulty_nodes = self.remove_unnecessary_nodes(faulty_nodes)
        return self.create_response(faulty_nodes, faulty_questions, faulty_tags), True if len(faulty_questions) > 0 else False

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

    def update_status(self, kt_id, language, doc_id, status, status_code, percentage, api_key):
        try:
            headers ={"apikey" : api_key, "Content-Type" : "application/json"}
            data = {"kt_id" : kt_id, "language" : language, "dockId" : doc_id, "status" : status, "percentage" : percentage*100}
            host_url = qna_conf.get('HOST_URL')
            status_update_endpoint = conf.get("STATUS_UPDATE_ENDPOINT")
            status_update_url = host_url + status_update_endpoint
            response = requests.post(status_update_url, data=json.dumps(data), headers=headers, timeout=1, verify = remote_config.get('ENV_SSL_VERIFY', False))
        except Exception as e:
            oa_logger.debug(e)
        return True

    def tanimoto(self, question_parts, path_list):
        return float(len(set(question_parts) & set(path_list)))/(len(set(question_parts) | set(path_list)))


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

    def check_for_better_matched_paths(self, root_node, parent_faq_map, parent_tags_map):
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
                for question_id,question in enumerate(questions):
                    better_path = self.check_if_there_is_a_better_path(question, all_paths, path_list)
                    if len(better_path) > 0:
                        if count < self.limits.get('better_matched_paths_limit'):
                            count += 1
                            faulty_nodes.append(path_list)
                            faulty_questions.append((str(questions[0]), better_path))
                            faulty_tags.append([])
                            better_paths[str([questions[0]] + path_list)] = better_path
                            break
        return self.create_response(faulty_nodes, faulty_questions, faulty_tags), True if len(faulty_questions) > 0 else False

    def fetch_ontology(self, kt_id, lang):
        res_taxonomy = self.db_manager.get_taxonomy(kt_id, lang)
        res_global_synonyms = self.db_manager.get_global_synonyms(kt_id)
        res_faqs = self.db_manager.get_faqs(kt_id, lang)
        parent_faq_map = dict()
        parent_tags_map = dict()
        nodes_with_faq_children = set()

        for faq_entry in res_faqs:

            all_tags = list()
            all_questions = list()

            nodes_with_faq_children.add(faq_entry['parent'])
            questions = [faq_entry.get('questionPayload').get('question')]
            tags = []

            tags_tmp = faq_entry.get('questionPayload').get('tagsPayload')
            tags.append(list({tag.get('tag')for tag in tags_tmp}))

            alternate_questions = faq_entry.get('subQuestions')
            for question in alternate_questions:
                if question.get('question').startswith("||"):
                    continue
                questions += [question.get('question')]
                tags_tmp = question.get('tagsPayload')
                tags.append(list({tag.get('tag') for tag in tags_tmp}))

            tags = list(tags)

            if faq_entry.get('parent') in parent_faq_map:
                all_tags = parent_tags_map.get(faq_entry.get('parent'))
                all_questions = parent_faq_map.get(faq_entry.get('parent'))
            all_tags.append(tags)
            all_questions.append(questions)
            parent_tags_map[faq_entry.get('parent')] = all_tags
            parent_faq_map[faq_entry.get('parent')] = all_questions

        parent_child_map = dict()
        synonyms_map = dict()
        term_usage_map = dict()
        parent_child_label_map = dict()
        for entry in res_taxonomy:
            synonyms_map[entry.get('nodeId')] = entry.get('synonyms')
            node_label = entry.get('label').lower()
            if node_label in res_global_synonyms:
                synonyms_map[entry.get('nodeId')]+=res_global_synonyms[node_label]
            term_usage_map[entry.get('nodeId')] = entry.get('termUsage')
            if len(entry.get('parent')) > 0:
                parent = entry.get('parent')[0]
            else:
                parent = None
            if parent in parent_child_map:
                children = parent_child_map.get(parent)
                parent_child_map[parent] = children + [entry.get('nodeId')]
                children_label = parent_child_label_map.get(parent)
                parent_child_label_map[parent] = children_label + [entry['label']]
            else:
                parent_child_map[parent] = [entry['nodeId']]
                parent_child_label_map[parent] = [entry.get('label')]
        root = parent_child_map.get(None)


        root_node = self.build_tree(parent_child_map, parent_child_label_map, nodes_with_faq_children, synonyms_map, term_usage_map)
        return root_node, parent_faq_map, parent_tags_map

    def run_diagnostics(self, root_node, parent_faq_map, parent_tags_map):
        self.kt_id = 1234#request.get('knowledgeTaskId')
        self.language = 'en'#request.get('language')
        self.doc_id = 5555#request.get('dock_id')
        self.threshold = 50#request.get('pathCoverage',50)
        self.stopwords = ['how', 'why', 'when', 'where', 'which', 'who', 'during', 'describe', 'detail', 'is',
                              'many', 'much', 'should', 'was', 'will', 'within', 'whom', 'i', 'me', 'my']#StopWords.get_stop_words(self.kt_id, self.language)

        try:
            self.lemmatizer.set_language(self.language)
            oa_logger.info('Ontology analyzer started for KT ID: ' + str(self.kt_id))
            # root_node, parent_faq_map, parent_tags_map = self.fetch_ontology(self.kt_id, self.language)
            self.tree_traversal = [node for node in PreOrderIter(root_node)]
            response = dict()
            timestamp = datetime.datetime.utcnow().isoformat() + 'Z'

            # response['_id'] = self.kt_id
            # response['dock_id'] = self.doc_id
            # response['kt_id'] = self.kt_id
            response['timestamp'] = timestamp
            response['language'] = self.language
            
            suggestions = 0
            errors = 0
            warnings = 0

            # self.update_status(self.kt_id, self.language, self.doc_id, "IN_PROGRESS", 200, 0/10, api_key)

            result, present_or_not = self.check_for_identical_subtree_cousins(root_node)
            response['longest_identical_subtree_cousins'] = {'result': result, 'type' : 'suggestion'}
            suggestions += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 1 (longest_identical_subtree_cousins) done for KT ID: ' + str(self.kt_id) + ' and issue present: ' + str(present_or_not))
            # self.update_status(self.kt_id, self.language, self.doc_id, "IN_PROGRESS", 200, 1/11, api_key)

            result, present_or_not = self.check_for_leaves_without_FAQs(root_node)
            response['leaves_without_faqs'] = {'result': result, 'type' : 'suggestion'}
            suggestions += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 2 (leaves_without_faqs) done for KT ID: ' + str(self.kt_id) + ' and issue present: ' + str(present_or_not))
            # self.update_status(self.kt_id, self.language, self.doc_id, "IN_PROGRESS", 200, 2/11, api_key)

            result, present_or_not = self.check_for_chains_of_nodes(root_node, parent_faq_map, parent_tags_map)
            response['chains_of_nodes'] = {'result': result, 'type' : 'suggestion'}
            suggestions += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 3 (chains_of_nodes) done for KT ID: ' + str(self.kt_id) + ' and issue present: ' + str(present_or_not))
            # self.update_status(self.kt_id, self.language, self.doc_id, "IN_PROGRESS", 200, 3/11, api_key)

            result, present_or_not = self.check_for_duplicate_sibling_nodes(root_node)
            response['repeated_node_names'] = {'result': result, 'type' : 'warning'}
            warnings += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 4 (repeated_node_names) done for KT ID: ' + str(self.kt_id) + ' and issue present: ' + str(present_or_not))
            # self.update_status(self.kt_id, self.language, self.doc_id, "IN_PROGRESS", 200, 4/11, api_key)

            result, present_or_not = self.check_if_tree_is_too_long(root_node)
            response['tree_too_long'] = {'result': result, 'type' : 'warning'}
            warnings += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 5 (tree_too_long) done for KT ID: ' + str(self.kt_id) + ' and issue present: ' + str(present_or_not))
            # self.update_status(self.kt_id, self.language, self.doc_id, "IN_PROGRESS", 200, 5/11, api_key)

            result, present_or_not = self.check_unreachable_questions(root_node, parent_faq_map, parent_tags_map)
            response['unreachable_questions'] = {'result': result, 'type' : 'error'}
            errors += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 6 (unreachable_questions) done for KT ID: ' + str(self.kt_id) + ' and issue present: ' + str(present_or_not))
            # self.update_status(self.kt_id, self.language, self.doc_id, "IN_PROGRESS", 200, 6/11, api_key)

            result, present_or_not = self.check_for_better_matched_paths(root_node, parent_faq_map, parent_tags_map)
            response['better_matched_paths'] = {'result': result, 'type' : 'warning'}
            warnings += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 7 (better_matched_paths) done for KT ID: ' + str(self.kt_id) + ' and issue present: ' + str(present_or_not))
            # self.update_status(self.kt_id, self.language, self.doc_id, "IN_PROGRESS", 200, 7/11, api_key)

            result, present_or_not = self.check_overlapping_alternate_questions(parent_faq_map)
            response['overlapping_alternate_questions'] = {'result': result, 'type' : 'suggestion'}
            suggestions += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 8 (overlapping_alternate_questions) done for KT ID: ' + str(self.kt_id) + ' and issue present: ' + str(present_or_not))
            # self.update_status(self.kt_id, self.language, self.doc_id, "IN_PROGRESS", 200, 8/11, api_key)

            result, present_or_not = self.check_number_of_matched_paths_per_question(root_node, parent_faq_map, parent_tags_map)
            response['questions_with_multiple_matched_paths'] = {'result': result, 'type' : 'warning'}
            warnings += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 9 (questions_with_multiple_matched_paths) done for KT ID: ' + str(self.kt_id) + ' and issue present: ' + str(present_or_not))
            # self.update_status(self.kt_id, self.language, self.doc_id, "IN_PROGRESS", 200, 9/11, api_key)
            
            result, present_or_not = self.check_possible_new_nodes(root_node, parent_faq_map, parent_tags_map)
            response['possible_new_nodes'] = {'result': result, 'type' : 'warning'}
            warnings += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 10 (possible_new_nodes) done for KT ID: ' + str(self.kt_id) + ' and issue present: ' + str(present_or_not))
            # self.update_status(self.kt_id, self.language, self.doc_id, "IN_PROGRESS", 200, 10/11, api_key)

            result, present_or_not = self.check_questions_at_root(root_node, parent_faq_map, parent_tags_map)
            response['questions_at_root'] = {'result': result, 'type' : 'suggestion'}
            suggestions += int(present_or_not)
            oa_logger.debug('Ontology analyzer: Check 11 (questions_at_root) done for KT ID: ' + str(self.kt_id) + ' and issue present: ' + str(present_or_not))
            # self.update_status(self.kt_id, self.language, self.doc_id, "IN_PROGRESS", 200, 11/11, api_key)
            
            response['no_of_suggestions'] = suggestions
            response['no_of_errors'] = errors
            response['no_of_warnings'] = warnings

            response['total_no_of_issues'] = suggestions + errors + warnings

            oa_logger.info('Ontology analyzer ran for KT ID: ' + str(self.kt_id))
            #oa_logger.debug('Ontology analyzer response for kt_id ' + str(self.kt_id) + ' : ' + str(response))

            return response
            #self.ont_analyzer_db_manager.save_ontology_analyzer_report(response)
            # self.update_status(self.kt_id, self.language, self.doc_id, "SUCCESS", 200, 1, api_key)
        except Exception as e:
            #self.update_status(self.kt_id, self.language, self.doc_id, "FAILURE", 200, 1, api_key)
            oa_logger.debug(e)
            traceback.print_exc()

if __name__ == "__main__":
    oa = OntologyAnalyzer()
    request = {'dock_id': 'ds-c04f74e7-d30b-5576-a75d-901f7ea9abc1',
               'knowledgeTaskId': '5d81d8d0bd966a7b58cebef3',
               'language': 'en',
               'botId': 'st-b82bff3d-4059-54dd-8839-1a387d187934',
               'userId': 'u-1a87b0cb-4409-5bc1-91aa-5c1dc618a2b6',
               'pathCoverage': 100}
    oa.run_diagnostics(request, "api")
