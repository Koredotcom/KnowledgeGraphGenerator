from collections import defaultdict
from tqdm import tqdm
from common import nlp, BOT_NAME
from log.Logger import Logger
from analyzer.ontology_analyzer import OntologyAnalyzer
from nltk.util import ngrams
import copy
import traceback
import re

logger = Logger()
space_join = " ".join

class TaxonomyBasedGenerator(object):
    def __init__(self):
        pass

    def generate_ngrams(self, tokens, n):
        return list(ngrams(tokens, n))

    def generate_tree(self, graph_file, language):
        generator = OntologyAnalyzer()
        generator.file_path = graph_file
        generator.read_file()
        generator.language = language
        root_node = generator.build_tree("generate")
        return root_node

    def generate_possible_paths(self, tokens, node, paths):
        if not node.children:
            return paths
        paths_copy = copy.deepcopy(paths)
        match_count = 0
        for child_node in node.children:
            node_name = nlp(child_node.name[1])
            node_name = list(map(lambda x : x.lemma_.lower() , node_name))
            normalized_node_name = node_name[0]
            for n_name in node_name[1:]:
                normalized_node_name = space_join((normalized_node_name, n_name))
            if normalized_node_name in tokens:
                match_count += 1
                if match_count > 1:
                    paths_copy.extend(paths)
                paths_copy[-1][0].append(child_node.name[1])

                if child_node.is_leaf:
                    paths_copy[-1][1] = 1
                updated_paths = self.generate_possible_paths(tokens, child_node, [paths_copy[-1]])
                paths_copy.pop()
                paths_copy.extend(updated_paths)
        return paths_copy

    def resolve_paths(self, paths):
        complete_paths = list()
        intermediate_paths = list()
        for path in paths:
            if path[1] == 1:
                complete_paths.append(path)
            else:
                intermediate_paths.append(path)
        if len(complete_paths) > 0:
            complete_paths_len = list(map(lambda x : len(x[0]), complete_paths))
            out_idx = complete_paths_len.index(max(complete_paths_len))
            # how to handle multiple paths with same depth
            return complete_paths[out_idx]
        elif len(intermediate_paths) > 0:
            intermediate_paths_len = list(map(lambda x : len(x[0]), intermediate_paths))
            out_idx = intermediate_paths_len.index(max(intermediate_paths_len))
            # how to handle multiple paths with same depth
            return intermediate_paths[out_idx]

    def insert_question(self, question, root_node, stop_tokens):
        ques = nlp(question)
        tokens = list(map(lambda x : x.lemma_ , ques))
        tokens_n = self.generate_ngrams(tokens, 3)
        tokens_n.extend(self.generate_ngrams(tokens, 2))
        for word in tokens_n:
            if word not in stop_tokens:
                tokens.append(space_join(word))
        terms = [root_node.name[1]]
        paths = [[terms,0]]
        generated_paths = self.generate_possible_paths(tokens, root_node, paths)
        final_path = self.resolve_paths(generated_paths)
        terms = final_path[0][::-1]
        return terms

    def generate_graph(self, args, qna_object_map, stop_tokens):
        quest_ontology_map = defaultdict(dict)
        try:
            if args.get('graph_file_path') and args.get('graph_request_type'):
                root_node = self.generate_tree(args.get('graph_file_path'), args.get('language')) 
            for ques_id, qna_object in tqdm(qna_object_map.items()):
                quest_ontology_map[ques_id]['question'] = qna_object.question
                ques = nlp(qna_object.normalized_ques)
                tags = ''
                terms = self.insert_question(qna_object.normalized_ques, root_node, stop_tokens)
                quest_ontology_map[ques_id]['terms'] = terms
                tags = [tags] if tags else []
                quest_ontology_map[ques_id]['tags'] = tags
        except Exception:
            logger.error(traceback.format_exc())
            raise Exception('Failed in generating ontology')
        return quest_ontology_map