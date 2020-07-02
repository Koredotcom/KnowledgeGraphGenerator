from collections import defaultdict


class Optimiser(object):
    def __init__(self):
        pass

    @staticmethod
    def convert_terms_to_tags(ques_obj, tag_convertible_terms):
        terms_to_replace = []
        terms_not_to_replace = []
        for term in ques_obj['terms']:
            if term in tag_convertible_terms:
                terms_to_replace.append(term)
            else:
                terms_not_to_replace.append(term)
        ques_obj['terms'] = terms_not_to_replace
        ques_obj['tags'] += terms_to_replace
        return ques_obj

    @staticmethod
    def create_path_to_question_map(tag_term_map, alt_ques_map):
        path_to_questions_map = defaultdict(list)
        for que_id in alt_ques_map:
            qna = tag_term_map[que_id]
            path = tuple(reversed(qna['terms']))
            path_to_questions_map[path].append(que_id)
        return path_to_questions_map

    def convert_empty_terms_as_tags(self, response_payload, path_to_questions_map):
        tag_term_map = response_payload['tag_term_map']
        for path in path_to_questions_map:
            tag_convertible_terms = []
            current_path = path[:-1]
            while len(current_path) > 1:
                ques_present_in_path = path_to_questions_map.get(current_path, []) != []
                if not ques_present_in_path:
                    tag_convertible_terms.append(current_path[-1])
                current_path = current_path[:-1]
            if tag_convertible_terms:
                for que_id in path_to_questions_map[path]:
                    tag_term_map[que_id] = self.convert_terms_to_tags(tag_term_map[que_id], tag_convertible_terms)

    @staticmethod
    def move_nodes_to_parent_level(tag_term_payload, path_to_question_map, node_level=1, max_ques=2):
        for path in path_to_question_map:
            if len(path) == node_level + 1:
                if len(path_to_question_map[path]) < max_ques:
                    for que_id in path_to_question_map[path]:
                        qna = tag_term_payload[que_id]
                        qna_terms = list(reversed(qna['terms']))
                        terms_to_remove, qna['terms'] = qna_terms[node_level:], qna_terms[:node_level][::-1]
                        qna['tags'] += terms_to_remove
        return tag_term_payload

    def optimise_graph(self, response_payload):
        path_to_question_map = self.create_path_to_question_map(response_payload['tag_term_map'],
                                                                response_payload['altq_map'])
        self.convert_empty_terms_as_tags(response_payload, path_to_question_map)
        updated_path_to_question_map = self.create_path_to_question_map(response_payload['tag_term_map'], response_payload['altq_map'])
        response_payload['tag_term_map'] = self.move_nodes_to_parent_level(response_payload['tag_term_map'], updated_path_to_question_map)
        return response_payload
