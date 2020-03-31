#!/usr/bin/python


class StopWords:
    def __init__(self):
        pass

    english_question_words = {'how', 'why', 'when', 'where', 'which', 'who', 'during', 'describe', 'detail', 'is',
                              'many', 'much', 'should', 'was', 'will', 'within', 'whom', 'i', 'me', 'my'}


    @classmethod
    def get_stop_words(cls, file_data, lang):
        """ get language specific stop words """
        cls.file_data = file_data
        if lang in ['zh', 'zh_cn', 'zh_tw']:
            lang = 'zh_tw'
        elif lang in ["ja", "japanese"]:
            lang = 'ja'
        elif lang in ["id", "ms", "bahasa"]:
            lang = 'bahasa'

        stopwords = [] if 'kgParams' not in cls.file_data else cls.file_data['kgParams'][
            'stopWords'] if 'stopWords' in cls.file_data['kgParams'] else []
        stopwords = [] if stopwords is None else stopwords
        if lang in ['en', 'en_kore']:
            stopwords = set(set(stopwords) | cls.english_question_words) if lang == 'en_kore' else set(stopwords)
            return stopwords
        elif lang in ['kk']:
            return set()
        else:
            return set(stopwords)


if __name__ == '__main__':
    print(StopWords.get_stop_words('sv'))
