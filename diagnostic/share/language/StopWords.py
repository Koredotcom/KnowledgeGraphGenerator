#!/usr/bin/python

from ontology.DBManager import DBManager
from share.config.ConfigManager import ConfigManager

config_manager = ConfigManager()
lang_conf = config_manager.load_config(key="language")


class StopWords:
    def __init__(self):
        pass

    db_manager = DBManager()

    english_question_words = {'how', 'why', 'when', 'where', 'which', 'who', 'during', 'describe', 'detail', 'is',
                              'many', 'much', 'should', 'was', 'will', 'within', 'whom', 'i', 'me', 'my'}

    @classmethod
    def get_stop_words(cls, kt_id, lang):
        """ get language specific stop words """

        if lang in ['zh']:
            lang = 'zh_tw'
        elif lang in ["ja", "japanese"]:
            lang = 'ja'
        elif lang in ["id", "ms", "bahasa"]:
            lang = 'bahasa'

        if lang in ['en', 'en_kore']:
            stopwords = cls.db_manager.get_stopwords_for_ktid(kt_id, 'en')
            stopwords = set(set(stopwords) | cls.english_question_words) if lang == 'en_kore' else set(stopwords)
            return stopwords
        elif lang in ['kk']:
            return set()
        else:
            stopwords = cls.db_manager.get_stopwords_for_ktid(kt_id, lang)
            return set(stopwords)


if __name__ == '__main__':
    print(StopWords.get_stop_words('5d0896e8dfe653090dc3fb39', 'sv'))
