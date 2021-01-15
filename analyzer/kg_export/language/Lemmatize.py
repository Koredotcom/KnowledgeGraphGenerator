#!/usr/bin/python

import json
from pattern.en import lemma as lemma_en
from pattern.es import lemma as lemma_es
from pattern.it import lemma as lemma_it
from nltk.stem.isri import ISRIStemmer
from nltk.stem import RSLPStemmer
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from nltk import word_tokenize
from nltk.stem.snowball import SnowballStemmer
import tinysegmenter
from analyzer.kg_export.language.kazlemmatizer import kazakh_lemma_tokenizer

use_compound_split_german = False
if use_compound_split_german:
    import LanguageDetection

stem_ar = ISRIStemmer()
factory = StemmerFactory()
sastrawi_stemmer = factory.create_stemmer()     #arabic stemmer
stem_pt = RSLPStemmer()                         #portugese_brazalian stemmer
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
        return read_file("analyzer/kg_export/language/dictionary/english_dictionary.json")

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
        
    def lemmatize(self, sentence):
        """ lemmatize string for list i18n support """
        lang = self.lang
        if lang == 'es' or lang == 'spanish':
            return [lemma_es(word) for word in word_tokenize(sentence)]
        elif lang == 'fr' or lang == 'french':
            return [stem_fr.stem(word) for word in word_tokenize(sentence)]
        elif lang == 'de' or lang == 'german':
            if use_compound_split_german:
                sentence = LanguageDetection.split_compound(sentence, 'de')
            result = list()
            for word in word_tokenize(sentence):
                lemma_word = stem_de.stem(word)
                if word and word[0].isupper():
                    first_char = lemma_word[0]
                    remaining_str = lemma_word[1:] if len(lemma_word) > 1 else ''
                    result.append(first_char.upper() + remaining_str)
                else:
                    result.append(lemma_word)
            return result
            # return [lemma_de(word) for word in word_tokenize(sentence)]
        elif lang == 'it' or lang == 'italian':
            return [lemma_it(word) for word in word_tokenize(sentence)]
        elif lang == 'nl' or lang == 'dutch':
            return self.dutch_lemmatizer(sentence)
        elif lang == 'ar' or lang == 'arabic':
            return [stem_ar.stem(word) for word in word_tokenize(sentence)]
        elif lang == 'pt' or lang == 'portugese brazalian':
            return [stem_pt.stem(word) for word in word_tokenize(sentence)]
        elif lang == 'ru' or lang == 'russian':
            return [stem_ru.stem(word) for word in word_tokenize(sentence)]
        elif lang == 'sv' or lang == 'swedish':
            return [stem_sv.stem(word) for word in word_tokenize(sentence)]
        elif lang in ['zh', 'zh_cn', 'zh_tw'] or lang == 'chinese':
            return self.chinese_tokenize(sentence)
        elif lang in ["id","bhasa","ms","malay","indonesian"]:
            return sastrawi_stemmer.stem(str(sentence)).split(" ")
        elif lang in ["ja","japanese"]:
            return stem_ja.tokenize(sentence)
        elif lang == 'ko' or lang == 'korean':
            return word_tokenize(sentence)
        elif lang == 'fi' or lang == 'finnish':
            return word_tokenize(sentence)
        elif lang == 'pl' or lang == 'polish':
            return word_tokenize(sentence)
        elif lang == 'uk' or lang =='ukranian':
            return word_tokenize(sentence)
        elif lang == 'kk' or lang == 'kazakh':
            return kazakh_lemma_tokenizer(sentence)
        else:
            return self.english_lemmatizer(sentence)


    __call__ = lemmatize

if __name__ == "__main__":

    lemma = Lemmatizer()
    en_dict = EnglishDict()

    lemma.set_language('en')
    print(lemma("I considered the stand authoring while I $#ate chocolates banking webexs dbSupportPlus"))
    lemma.set_language('es')
    print(lemma('Recordé las PROnunciaciones mientras comía chocolates'))
    lemma.set_language('fr')
    print(lemma("J'ai rappelé les Prononciations pendant que j'ai mangé des chocolats"))
    lemma.set_language('de')
    print(' '.join(lemma("während ich's Schokolade aß binnenhandel binenhandel")))
    lemma.set_language('zh_cn')
    print(lemma("我在吃巧克力时考虑了桥梁发音"))
    lemma.set_language('id')
    print(lemma("dia berlari"))
    print(en_dict.is_english_word("recalled"))
    #print lemma('en')('CREated using penSil')

    lemma.set_language('ar')
    for lemma_ord in lemma("اين تعمل؟"):
        print(lemma_ord, end=' ')

    print("")

    lemma.set_language('ja')
    for lemma_ord in lemma("サイバーセキュリティとは"):
        print(lemma_ord)

    print("")
    lemma.set_language('fi')
    print(lemma('mikä on pääkaupunki Suomessa'))

    lemma.set_language('sv')
    print(lemma(' det här är att bilen går som en svullnad'))
