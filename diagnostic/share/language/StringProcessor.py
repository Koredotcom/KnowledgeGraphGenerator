""" StringProcessor class handles language specific string functions"""

import re
import sys
sys.path.append('./../')
from difflib import SequenceMatcher
from share.language.Lemmatize import Lemmatizer
from share.util import decorator


class StringProcessor(object):

    """ language specific string operations"""

    def __init__(self):
        self.contractions_dict = {
            "can't've": "cannot have",
            "couldn't've": "could not have",
            "hadn't've": "had not have",
            "he'd've": "he would have",
            "he'll've": "he will have",
            "how'd'y": "how do you",
            "I'd've": "I would have",
            "I'll've": "I will have",
            "it'd've": "it would have",
            "it'll've": "it will have",
            "mightn't've": "might not have",
            "mustn't've": "must not have",
            "needn't've": "need not have",
            "oughtn't've": "ought not have",
            "sha'n't": "shall not",
            "shan't've": "shall not have",
            "she'd've": "she would have",
            "she'll've": "she will have",
            "shouldn't've": "should not have",
            "that'd've": "that would have",
            "there'd've": "there would have",
            "they'd've": "they would have",
            "they'll've": "they will have",
            "we'd've": "we would have",
            "we'll've": "we will have",
            "what'll've": "what will have",
            "who'll've": "who will have",
            "won't've": "will not have",
            "wouldn't've": "would not have",
            "y'all'd": "you all would",
            "y'all're": "you all are",
            "y'all've": "you all have",
            "you'd've": "you would have",
            "you'll've": "you will have",
            "ain't": "is not",
            "aren't": "are not",
            "can't": "cannot",
            "'cause": "because",
            "could've": "could have",
            "couldn't": "could not",
            "didn't": "did not",
            "doesn't": "does not",
            "don't": "do not",
            "hadn't": "had not",
            "hasn't": "has not",
            "haven't": "have not",
            "he'd": "he would",
            "he'll": "he will",
            "he's": "he is",
            "how'd": "how did",
            "how'll": "how will",
            "how's": "how is",
            "i'd": "I would",
            "i'll": "I will",
            "i'm": "I am",
            "i've": "I have",
            "isn't": "is not",
            "it'd": "it would",
            "it'll": "it will",
            "it's": "it is",
            "let's": "let us",
            "ma'am": "madam",
            "mayn't": "may not",
            "might've": "might have",
            "mightn't": "might not",
            "must've": "must have",
            "mustn't": "must not",
            "needn't": "need not",
            "o'clock": "of the clock",
            "oughtn't": "ought not",
            "shan't": "shall not",
            "she'd": "she would",
            "she'll": "she will",
            "she's": "she is",
            "should've": "should have",
            "shouldn't": "should not",
            "so've": "so have",
            "so's": "so is",
            "that'd": "that had",
            "that's": "that is",
            "there'd": "there would",
            "there's": "there is",
            "they'd": "they would",
            "they'll": "they will",
            "they're": "they are",
            "they've": "they have",
            "to've": "to have",
            "wasn't": "was not",
            "we'd": "we would",
            "we'll": "we will",
            "we're": "we are",
            "we've": "we have",
            "weren't": "were not",
            "what'll": "what will",
            "what're": "what are",
            "what's": "what is",
            "what've": "what have",
            "when's": "when is",
            "when've": "when have",
            "where'd": "where did",
            "where's": "where is",
            "where've": "where have",
            "who'll": "who will",
            "who's": "who is",
            "who've": "who have",
            "why's": "why is",
            "why've": "why have",
            "will've": "will have",
            "won't": "will not",
            "would've": "would have",
            "wouldn't": "would not",
            "y'all": "you all",
            "you'd": "you would",
            "you'll": "you will",
            "you're": "you are",
            "you've": "you have"""
        }

        self.contractions_re = re.compile(
            '(%s)' %
            '|'.join(list(self.contractions_dict.keys())), re.IGNORECASE)
        self.lemmatizer = Lemmatizer()

    def expand_contractions(self, input_string):
        """ exapand standard english language contractions """
        try:
            def replace(match):
                """ replace matched string"""
                return self.contractions_dict[match.group(0).lower()]
            return self.contractions_re.sub(replace, input_string)
        except:
            return input_string

    def normalize(self, input_string, language_code):
        """ clean and leammatize string"""
        self.lemmatizer.set_language(language_code)
        return_string = input_string
        if language_code == 'en':
            expanded_string = self.expand_contractions(input_string)
            if expanded_string.find("'") != -1:
                expanded_string = self.expand_contractions(expanded_string)

            return_string = re.sub(
                r'\W+',
                ' ',
                expanded_string)  # Remove Non AlphaNumeric Character

        return ' '.join(self.lemmatizer(return_string))

    @staticmethod
    def near_match(query_input, graph_input_question   ):
        """ cehck the sequence matcher score"""
        fuzzScore = SequenceMatcher(None, query_input.lower(), graph_input_question.lower()).ratio()
        return fuzzScore
        
    @staticmethod
    def fuzzy_match(query_input, graph_input_question   ):
        """"Return the ratio of the most similar substring
        as a number between 0.0 and 1.0"""

        if len(query_input) <= len(graph_input_question):
            #return SequenceMatcher(None, query_input.lower(), graph_input_question.lower()).ratio()
            shorter = query_input
            longer = graph_input_question
        else:
            shorter = graph_input_question
            longer = query_input

        m = SequenceMatcher(None, shorter, longer)
        blocks = m.get_matching_blocks()

        # each block represents a sequence of matching characters in a string
        # of the form (idx_1, idx_2, len)
        # the best partial match will block align with at least one of those blocks
        #   e.g. shorter = "abcd", longer = XXXbcdeEEE
        #   block = (1,3,3)
        #   best score === ratio("abcd", "Xbcd")
        scores = []
        for block in blocks:
            long_start = block[1] - block[0] if (
                block[1] - block[0]) > 0 else 0
            long_end = long_start + len(shorter)
            long_substr = longer[long_start:long_end]

            m2 = SequenceMatcher(None, shorter, long_substr)
            r = m2.ratio()
            if r > .995:
                return 1.0
            else:
                scores.append(r)

        score = int(round(100 * max(scores)))
        return score / 100.0

    @staticmethod
    def is_faq(query):
        if not len(query):
            return False
        updated_query = ' '.join(query.split()).lower()
        if updated_query[-1] == '?':
            return True

        question_words = ['who', 'what', 'why', 'when', 'where', 'which', 'how', 'define', 'explain', 'mean', 'help', 'meaning','did' , 'do' , 'are' , 'shall' , 'must' , 'may' , 'can' , 'do' , 'is' , 'are' , 'am' , 'were' , 'will' , 'might' , 'could' , 'should', 'does', 'tell', 'give']

        if updated_query.startswith(tuple(question_words)):
            return True

        return False

if __name__ == "__main__":
    stringProcessor = StringProcessor()
# print(stringProcessor.normalize("what's the working PURPOSE      OF#$
# BANKing LIfe?", 'en'))
    print(stringProcessor.fuzzy_match('what is india', 'what is india'))
