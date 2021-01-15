import spacy


def get_answer_object():
    answer_obj = [
        {
            'text': '',
            'type': '',
            'channel': ''
        }
    ]
    return answer_obj


model = "en_core_web_sm"
nlp = spacy.load(model, disable=["ner"])

PHRASES_FREQ_THRESHOLD = 2
UNIGRAM_FREQ_THRESHOLD = 5
BOT_NAME = 'Auto Ontology'
JSON_TEMPLATE = {
    'question': '',
    'alternateQuestions': [],
    'terms': [],
    'tags': [],
    'refId': '',
    'responseType': 'message',
    'answer': [],
    'alternateAnswers': []
}
