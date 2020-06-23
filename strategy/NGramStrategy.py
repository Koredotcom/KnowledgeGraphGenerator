from collections import defaultdict
from tqdm import tqdm
from common import nlp, BOT_NAME
from strategy.phrase_finder import PhraseFinder
from log.Logger import Logger
import copy
import traceback
import re

logger = Logger()
phrase_finder_obj = PhraseFinder()


class GramBasedGenerator(object):
    def __init__(self):
        pass

    @staticmethod
    def _filter_substrings(node_names):
        new_node_names = copy.deepcopy(node_names)
        for node_1 in node_names:
            node_1_stripped = node_1.strip()
            for node_2 in node_names:
                node_2_stripped = node_2.strip()
                try:
                    if node_1_stripped != node_2_stripped:
                        if node_2_stripped in node_1_stripped:
                            new_node_names.remove(node_2)
                except Exception:
                    pass
        return new_node_names

    @staticmethod
    def add_tag_to_single_word_questions(ques, stop_tokens):
        tag = ''
        try:
            ques = ques.strip()
            ques = ques[:-1] if ques.endswith('?') else ques
            ques_word_set = set(ques.lower().split()).difference(stop_tokens)
            if len(ques_word_set) == 1:
                tag = list(ques_word_set)[0]
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            return tag

    def generate_graph(self, qna_object_map, stop_tokens):
        normalized_ques_list = [qna_obj.normalized_ques for qna_obj in qna_object_map.values()]
        phrases, uni_tokens, verbs = phrase_finder_obj.find_all_phrases(normalized_ques_list, stop_tokens)
        most_commons_terms = dict()
        most_commons_terms.update(phrases.most_common())
        most_commons_terms.update(uni_tokens.most_common())
        most_commons_terms.update(verbs.most_common())
        quest_ontology_map = defaultdict(dict)
        logger.info('Initiated ontology generation')
        try:
            for ques_id, qna_object in tqdm(qna_object_map.items()):
                ques = qna_object.normalized_ques
                quest_ontology_map[ques_id]['question'] = qna_object.question
                tags = ''
                terms = list()
                q = copy.deepcopy(ques)
                doc = nlp(q)
                doc = " ".join([t.lemma_ if t.lemma_ != "-PRON-" else t.text for t in doc])


                for term, cnt in phrases.most_common():
                    if cnt == 1:
                        break
                    if term in stop_tokens:
                        continue
                    try:
                        regex = re.compile("\\b" + term + "\\b")
                        if re.findall(regex, doc) and cnt > 1:
                            doc = re.sub(regex, "~~~~", doc)
                            terms.append(term)
                    except Exception:
                        print(traceback.format_exc())

                for term, cnt in uni_tokens.most_common():
                    if cnt == 1:
                        break
                    if term in stop_tokens:
                        continue
                    try:
                        regex = re.compile("\\b" + term + "\\b")
                        if re.findall(regex, doc):
                            doc = re.sub(regex, "~~~~", doc)
                            terms.append(term)
                    except Exception:
                        print(traceback.format_exc())

                for term, cnt in verbs.most_common():
                    if cnt == 1:
                        break
                    try:
                        regex = re.compile("\\b" + term + "\\b")
                        if re.findall(regex, doc):
                            tags = term
                    except Exception:
                        pass

                if not (terms or tags):
                    tags = self.add_tag_to_single_word_questions(qna_object.question, stop_tokens)

                terms = sorted(self._filter_substrings(terms), key=lambda x: most_commons_terms[x]) + [BOT_NAME]
                quest_ontology_map[ques_id]['terms'] = terms
                tags = [tags] if tags else []
                quest_ontology_map[ques_id]['tags'] = tags
        except Exception:
            logger.error(traceback.format_exc())
            raise Exception('Failed in generating ontology')

        return quest_ontology_map
