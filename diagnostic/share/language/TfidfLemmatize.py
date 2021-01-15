#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import tinysegmenter
from pattern.en import lemma as lemma_en
from pattern.es import lemma as lemma_es
from nltk import word_tokenize
from nltk.stem.isri import ISRIStemmer
from nltk.stem.snowball import SnowballStemmer
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from share.language.kazlemmatizer import kazakh_lemma_tokenizer
from share.config.ConfigManager import ConfigManager
from konlpy.tag import Mecab

config_manager = ConfigManager()
lang_config = config_manager.load_config('language')

MECAB_KO_DIR = lang_config.get('KOREAN_TOKENIZER_DICT_PATH', '')
if MECAB_KO_DIR:
    mecab = Mecab(MECAB_KO_DIR)

use_compound_split_german = lang_config.get('ENABLE_LANGUAGE_DETECTION', False)
if use_compound_split_german:
    import LanguageDetection

stem_ar = ISRIStemmer()
factory = StemmerFactory()
sastrawi_stemmer = factory.create_stemmer()
stem_ja = tinysegmenter.TinySegmenter()
stem_nl = SnowballStemmer('dutch')
stem_ru = SnowballStemmer('russian')
stem_sv = SnowballStemmer('swedish')
stem_fr = SnowballStemmer('french')
stem_de = SnowballStemmer('german')

def read_file(filename):
    try:
        with open(filename, "r") as file_dp:
            data = json.load(file_dp)
            return data
    except Exception:
        return {}

nl_compound_word_map = read_file("share/language/dictionary/nl_compound_words.json")


class Lemmatizer:

    def __init__(self, lang):
        self.lang = lang

    def chinese_tokenize(self,sentence):
        tokens = []
        temp = ""
        for charecter in sentence:
            if charecter  > '\u4e00' and charecter < '\u9fff':
                if temp != "":
                    tokens.extend(temp.strip().split(" "))
                    temp=""
                tokens.append(charecter)
            else:
                temp+=str(charecter)
        if temp != "":
            tokens.extend(temp.strip().split(" "))
        return tokens

    def dutch_lemmatizer(self,sentence):
        lemma_list = []
        for word in word_tokenize(sentence):
            if word in nl_compound_word_map:
                try:
                    nl_lemma_map = nl_compound_word_map[word].replace("+", "||").replace("_", "||").replace(" ","").split("||")
                except:
                    nl_lemma_map = [word]
                lemma_list += nl_lemma_map
            else:
                lemma_list.append(stem_nl.stem(word))
        return lemma_list

    def getKoLemmaTokens(self, doc):
        tokens = mecab.pos(doc)
        return [token[0] for token in tokens]

    def lemmatize(self, sentence):
        """ lemmatize string for list i18n support """
        lang = self.lang.lower()
        if lang == 'es' or lang == 'spanish':
            return [lemma_es(word) for word in word_tokenize(sentence)]
        elif lang == 'fr' or lang == 'french':
            return [stem_fr.stem(word) for word in word_tokenize(sentence)]
        elif lang == 'de' or lang == 'german':
            result = list()
            if use_compound_split_german:
                sentence, _ = LanguageDetection.split_compound(sentence, 'de')
            for word in word_tokenize(sentence):
                lemma_word = stem_de.stem(word)
                if word and word[0].isupper():
                    first_char = lemma_word[0]
                    remaining_str = lemma_word[1:] if len(lemma_word) > 1 else ''
                    result.append(first_char.upper() + remaining_str)
                else:
                    result.append(lemma_word)
            return result
        elif lang in ['nl','dutch']:
            return self.dutch_lemmatizer(sentence)
        elif lang == 'ar' or lang == 'arabic':
            return [stem_ar.stem(word) for word in word_tokenize(sentence)]
        elif lang == 'ru' or lang == 'russian':
            return [stem_ru.stem(word) for word in word_tokenize(sentence)]
        elif lang == 'sv' or lang == 'swedish':
            return [stem_sv.stem(word) for word in word_tokenize(sentence)]
        elif lang == 'zh' or lang == 'chinese':
            return self.chinese_tokenize(sentence)
        elif lang in ["id","bhasa","ms","malay","indonesian"]:
            return sastrawi_stemmer.stem(str(sentence)).split(" ")
        elif lang in ["ja","japanese"]:
            return stem_ja.tokenize(sentence)
        elif lang == 'ko' or lang == 'korean':
            return self.getKoLemmaTokens(sentence)
        elif lang == 'fi' or lang == 'finnish':
            return word_tokenize(sentence)
        elif lang == 'pl' or lang == 'polish':
            return word_tokenize(sentence)
        elif lang == 'uk' or lang == 'ukranian':
            return word_tokenize(sentence)
        elif lang == 'kk' or lang == 'kazakh':
            return kazakh_lemma_tokenizer(sentence)
        else:
            return [lemma_en(word) for word in word_tokenize(sentence)]

    __call__ = lemmatize

if __name__ == "__main__":

    lemma = Lemmatizer('en')
    print(lemma('I RECALLED the Pronunciations while I $#ate chocolates banking '))
    lemma = Lemmatizer('es')
    print(lemma('Recordé las PROnunciaciones mientras comía chocolates'))
    lemma = Lemmatizer('fr`')
    print(lemma("J'ai rappelé les Prononciations pendant que j'ai mangé des chocolats"))
    lemma = Lemmatizer('de')
    print(lemma('während ich Schokolade aß binnenhandel binenhandel'))

    print(Lemmatizer('en')('CREated using penSil'))
    lemma = Lemmatizer('fi')
    print(lemma('mikä on pääkaupunki Suomessa'))

    lemma = Lemmatizer('ko')
    print(lemma('ik heb een wiebelende tap'))
    print(lemma('c02 is een probleem'))
    print(lemma('이것은 토크 나이저를 미리로드하는 것입니다.'))
