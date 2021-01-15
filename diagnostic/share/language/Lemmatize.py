#!/usr/bin/python

import json
import os
import logging
import traceback
from pattern.en import lemma as lemma_en
# from pattern.es import lemma as lemma_es
# from pattern.it import lemma as lemma_it
# from nltk.stem.isri import ISRIStemmer
# from nltk.stem import RSLPStemmer
# from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from nltk import word_tokenize
from nltk.stem.snowball import SnowballStemmer
import tinysegmenter
#from konlpy.tag import Mecab
# from share.language.kazlemmatizer import kazakh_lemma_tokenizer
# from share.config.ConfigManager import ConfigManager

# debug_logger = logging.getLogger('debug')

# config_manager = ConfigManager()
# lang_config = config_manager.load_config('language')
# st_conf = config_manager.load_config(key='storage')





def read_file(filename):
    try:
        with open(filename, "r") as file_dp:
            data = json.load(file_dp)
            return data
    except Exception:
        return {}

nl_compound_word_map = read_file("share/language/dictionary/nl_compound_words.json")


class Singleton(object):
    """
    Singleton interface:
    http://www.python.org/download/releases/2.2.3/descrintro/#__new__
    """

    def __new__(cls, *args, **kwds):
        it = cls.__dict__.get("__it__")
        if it is not None:
            return it
        cls.__it__ = it = object.__new__(cls)
        it.init(*args, **kwds)
        return it

    def init(self, *args, **kwds):
        pass

class EnglishDict(Singleton):
    def init(self):
        self.en_dictionary = self.load_en_dictionary()

    def load_en_dictionary(self):
        return read_file("./share/language/dictionary/english_dictionary.json")

    def is_english_word(self, word):
        try:
            x = self.en_dictionary[word.lower()]
            return True
        except KeyError:
            return False

en_dict = EnglishDict()

class Lemmatizer:

    def __init__(self):
        self.lang = 'aa'
        self.english_edit = {'banking': 'bank', 'us':'us', 'timing':'time', 'timings':'time'}


        
    def set_language(self, lang):
        """ set language"""
        self.lang = lang
        
    def english_lemmatizer(self, sentence):
        """ english lemma"""
        lemma_list = []
        for word in word_tokenize(sentence):
            lowercase_word = word.lower()
            if lowercase_word in self.english_edit:
                lemma_list.append(self.english_edit[lowercase_word])
            elif en_dict.is_english_word(lowercase_word):
                lemma_list.append(lemma_en(lowercase_word))
            else:
                lemma_list.append(lowercase_word)
        return lemma_list

    
    def lemmatize(self, sentence):
        """ lemmatize string for list i18n support """
        #lang = self.lang
        
            # return [lemma_de(word) for word in word_tokenize(sentence)]
        
       
        return self.english_lemmatizer(sentence)


    __call__ = lemmatize

if __name__ == "__main__":
    lemma = Lemmatizer()
    en_dict = EnglishDict()

    lemma.set_language('en')
    print(lemma("I considered the childrens Pronunciations while I $#ate chocolates banking webexs dbSupportPlus"))
    
