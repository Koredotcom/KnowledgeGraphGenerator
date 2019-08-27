from collections import Counter
import textacy
from nltk.util import ngrams
from tqdm import tqdm
from common import *

space_join = " ".join


class PhraseFinder(object):
    def __init__(self):
        pass

    def find_all_phrases(self, question_list, stop_tokens):
        """
        :param stop_tokens: set
        :type question_list: list
        """
        all_tokens = []
        uni_tokens = []
        all_verbs = []
        for question in tqdm(question_list):
            bi_tri_grams, unigrams, verbs = self.find_phrases(question, stop_tokens)
            all_tokens.extend(bi_tri_grams)
            uni_tokens.extend(unigrams)
            all_verbs.extend(verbs)
        all_token_counter = Counter(all_tokens)
        unigram_counter = Counter(uni_tokens)
        verb_counter = Counter(all_verbs)

        phrases = [[p, cnt] for p, cnt in all_token_counter.most_common() if cnt > PHRASES_FREQ_THRESHOLD]
        uni_tokens = [[p, cnt] for p, cnt in unigram_counter.most_common() if cnt > UNIGRAM_FREQ_THRESHOLD]
        all_tokens = copy.deepcopy(phrases)

        for phrase, phrase_count in phrases:
            for sub_phrase, sub_phrase_cnt in phrases:
                if sub_phrase != phrase:
                    try:
                        if sub_phrase in phrase and sub_phrase_cnt == phrase_count:
                            all_tokens.remove([sub_phrase, sub_phrase_cnt])
                    except Exception:
                        pass
        return Counter({t: c for t, c in all_tokens}), Counter({t: c for t, c in uni_tokens}), verb_counter

    def find_phrases(self, sentence, stop_tokens):
        doc = nlp(sentence)
        doc_grams = []
        unigrams = []
        for i in doc.noun_chunks:
            text = " ".join([t.lemma_ if t.lemma_ != "-PRON-" else t.text for t in i])
            tokens = [t for t in text.split() if t != "" and t not in stop_tokens]
            unigrams.extend(tokens)
            grams = self.generate_ngrams(tokens, 3)
            grams.extend(self.generate_ngrams(tokens, 2))
            for e in grams:
                if e not in stop_tokens:
                    doc_grams.append(space_join(e))

        pattern = r'<VERB>?<ADV>*<VERB>+'
        doc = textacy.Doc(sentence, lang=model)
        lists = textacy.extract.pos_regex_matches(doc, pattern)
        verbs = []
        for l in lists:
            v_tokens = l.lemma_.split()
            for v in v_tokens:
                if v not in stop_tokens:
                    verbs.append(v)
        return doc_grams, unigrams, verbs

    def generate_ngrams(self, tokens, n):
        return list(ngrams(tokens, n))
