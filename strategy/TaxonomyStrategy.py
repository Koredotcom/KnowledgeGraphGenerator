from collections import defaultdict
from tqdm import tqdm
from log.Logger import Logger
from analyzer.ontology_analyzer import OntologyAnalyzer
from request_type.CSVExportParser import CSVExportParser
from request_type.CSVParser import CSVParser as csvParser
from request_type.JSONExportParser import JSONExportParser as jsonParser
from StringProcessor import StringProcessor
from nltk.util import ngrams
from nltk.stem import WordNetLemmatizer 
from nltk import word_tokenize
import copy
import traceback
import re

lemmatizer = WordNetLemmatizer()
logger = Logger()
string_processor = StringProcessor()
space_join = " ".join

PATH_INDEX = 0
PATH_IDX_INDEX = 1
PATH_MATCH_PERCENTAGE_INDEX = 2
LEN_MATCHED_NODES_INDEX = 3
NO_CONSECUTIVE_MATCH_INDEX = 4

class TaxonomyBasedGenerator(object):
    def __init__(self):
        pass

    @staticmethod
    def get_input_parser(request_type):
        if request_type == 'json_export':
            return jsonParser
        elif request_type == 'csv':
            return csvParser
        elif request_type == 'csv_export':
            return CSVExportParser

    def generate_ngrams(self, tokens, n):
        return list(ngrams(tokens, n))

    def intersection(self, lst1, lst2):
        temp = set(lst2)
        lst3 = [value for value in lst1 if value in temp]
        return lst3

    def normalize_string(self, input_string, lang_code):
        return string_processor.normalize(input_string, lang_code)

    def pre_process_nodes(self, paths, lang_code):
        lemmatized_paths = list()
        for ix, path in paths:
            lemmatized_path = [lemmatizer.lemmatize(self.normalize_string(w, lang_code)) for w in path]
            lemmatized_paths.append((ix,lemmatized_path))
        return lemmatized_paths

    def generate_tree(self, graph_file, language):
        generator = OntologyAnalyzer()
        generator.file_path = graph_file
        generator.read_file()
        generator.language = language
        root_node = generator.build_tree("generate")
        return root_node

    def shortlist_possible_paths(self, tokens, paths):
        path_match_info = list()
        complete_match_count = 0
        for path_ix, path in paths:
            single_leaf_node_matched = False
            matched_nodes = self.intersection(path, tokens)
            path_match_percentage = len(matched_nodes)/(len(path) - 1 )
            if path_match_percentage == 1:
                complete_match_count += 1
                consecutive_match_no = len(matched_nodes)

            if complete_match_count == 0:
                if len(matched_nodes) > 1:
                    matched_nodes_n = self.generate_ngrams(matched_nodes, 2)
                    path_n = self.generate_ngrams(path, 2)
                    consecutive_match_no = len(self.intersection(path_n, matched_nodes_n))
                elif len(matched_nodes) == 1:
                    consecutive_match_no = 0
                    if matched_nodes[0] == path[-1]:
                        single_leaf_node_matched = True
                else:
                    consecutive_match_no = 0

            if not single_leaf_node_matched:
                if (complete_match_count == 0 and path_match_percentage > 0) or (complete_match_count > 0 and path_match_percentage == 1) :
                    temp_list = [None] * 5
                    temp_list[PATH_INDEX] = path
                    temp_list[PATH_IDX_INDEX] = path_ix
                    temp_list[PATH_MATCH_PERCENTAGE_INDEX] = path_match_percentage
                    temp_list[LEN_MATCHED_NODES_INDEX] = len(matched_nodes)
                    temp_list[NO_CONSECUTIVE_MATCH_INDEX] = consecutive_match_no
                    path_match_info.append(temp_list)
        return path_match_info

    def resolve_paths(self, paths_info):
        complete_paths = list()
        intermediate_paths = list()
        if len(paths_info) == 0:
            return paths_info
        for path_info in paths_info:
            if path_info[PATH_MATCH_PERCENTAGE_INDEX] == 1:
                complete_paths.append(path_info)
            else:
                intermediate_paths.append(path_info)

        if len(complete_paths) > 0:
            complete_paths_len = list(map(lambda x : len(x[PATH_INDEX]), complete_paths))
            out_idx = complete_paths_len.index(max(complete_paths_len))
            return complete_paths[out_idx]

        elif len(intermediate_paths) > 0:
            consecutive_match_no = list(map(lambda x : x[NO_CONSECUTIVE_MATCH_INDEX], intermediate_paths))
            c_max = max(consecutive_match_no)
            max_consecutive_matched_nodes_idx = [i for i, j in enumerate(consecutive_match_no) if j == c_max]
            
            if len(max_consecutive_matched_nodes_idx) == 1:
                out_idx = max_consecutive_matched_nodes_idx[0]
                return intermediate_paths[out_idx]
            
            match_nodes_no = [intermediate_paths[idx][LEN_MATCHED_NODES_INDEX] for idx in max_consecutive_matched_nodes_idx]
            m_max = max(match_nodes_no)
            if m_max == 1:
                match_nodes_percentage = [intermediate_paths[idx][PATH_MATCH_PERCENTAGE_INDEX] for idx in max_consecutive_matched_nodes_idx]
                temp_idx = match_nodes_percentage.index(max(match_nodes_percentage))
            else:
                temp_idx = match_nodes_no.index(m_max)
            out_idx = max_consecutive_matched_nodes_idx[temp_idx]
            return intermediate_paths[out_idx]

    def insert_question(self, question, original_paths, paths, stop_tokens):
        terms = list()
        try:
            tokens = word_tokenize(question)
            tokens = [lemmatizer.lemmatize(w) for w in tokens]
            tokens_n = self.generate_ngrams(tokens, 3)
            tokens_n.extend(self.generate_ngrams(tokens, 2))
            for word in tokens_n:
                if word not in stop_tokens:
                    tokens.append(space_join(word))
            shortlisted_paths_info = self.shortlist_possible_paths(tokens, paths)
            final_path = self.resolve_paths(shortlisted_paths_info)
            if len(final_path) == 0:
                terms = [original_paths[0][1][0]]   # root node name
            else:
                path_idx = final_path[PATH_IDX_INDEX]
                terms = original_paths[path_idx][1][::-1]
                #terms = final_path[0][::-1]
        except:
            print('Error in inserting question !!!, go through log/auto_kg.log for detailed report')
            logger.error(traceback.format_exc())
        return terms

    def generate_graph(self, args, qna_object_map, stop_tokens):
        quest_ontology_map = defaultdict(dict)
        try:
            if args.get('graph_file_path') and args.get('graph_request_type'):
                graph_input_parser = self.get_input_parser(args.get('graph_request_type'))
                original_paths = graph_input_parser(args).parse(args.get('graph_file_path'), 'graph').get('paths')
                paths = self.pre_process_nodes(original_paths, args.get('lang_code'))
                #root_node = self.generate_tree(args.get('graph_file_path'), args.get('language'))
            else:
                # add logic for other cases to generate the paths
                paths = []
                original_paths = [] 
            for ques_id, qna_object in tqdm(qna_object_map.items()):
                quest_ontology_map[ques_id]['question'] = qna_object.question
                tags = ''
                terms = self.insert_question(qna_object.normalized_ques, original_paths, paths, stop_tokens)
                quest_ontology_map[ques_id]['terms'] = terms
                tags = [tags] if tags else []
                quest_ontology_map[ques_id]['tags'] = tags
        except Exception:
            logger.error(traceback.format_exc())
            raise Exception('Failed in generating ontology')
        return quest_ontology_map