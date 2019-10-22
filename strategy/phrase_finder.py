from collections import Counter
from nltk.util import ngrams
from tqdm import tqdm
from common import PHRASES_FREQ_THRESHOLD, UNIGRAM_FREQ_THRESHOLD, model, nlp
import copy
import textacy

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

    @staticmethod
    def is_valid_word(word):
        if len(word) > 1:
            return True
        return False

    def find_phrases(self, sentence, stop_tokens):
        doc = nlp(sentence)
        doc_grams = []
        unigrams = []
        for i in doc.noun_chunks:
            text = " ".join([t.lemma_ if t.lemma_ != "-PRON-" else t.text for t in i])
            tokens = [t for t in text.split() if t != "" and t not in stop_tokens]
            unigrams.extend(list(filter(lambda word: self.is_valid_word(word), tokens)))
            grams = self.generate_ngrams(tokens, 3)
            grams.extend(self.generate_ngrams(tokens, 2))
            for word in grams:
                if word not in stop_tokens:
                    doc_grams.append(space_join(word))

        pattern = r'<VERB>?<ADV>*<VERB>+'
        doc = textacy.Doc(sentence, lang=model)
        lists = textacy.extract.pos_regex_matches(doc, pattern)
        verbs_list = []
        for l in lists:
            verb_tokens = l.lemma_.split()
            for verb in verb_tokens:
                if verb not in stop_tokens and self.is_valid_word(verb):
                    verbs_list.append(verb)
        return doc_grams, unigrams, verbs_list

    def generate_ngrams(self, tokens, n):
        return list(ngrams(tokens, n))


if __name__ == "__main__":
    a = 'How does the e-monies NEFT service differ from RGTS and EFT?'
    from StopWords import StopWords
    from StringProcessor import StringProcessor

    a = StringProcessor().normalize(a, 'en')
    en = StopWords.get_stop_words('en')
    cl = PhraseFinder()
    print(cl.find_phrases(a, en))
