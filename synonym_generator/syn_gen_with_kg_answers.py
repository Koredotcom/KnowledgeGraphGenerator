import csv
import json
import sys
import pandas as pd
from nltk import word_tokenize
from tqdm import tqdm
from gensim.models import Word2Vec

def json_export_to_answers(file_path):
    output_file_path = "answer.csv"
    faq_answers = []

    with open(file_path) as json_data:
        json_faqs = json.load(json_data)
        faqs = json_faqs['faqs']
        c = 0
        considered = set()
        for faq in faqs:
            if not 'answer' in faq  or faq['answer'][0]['text'] in considered:
                continue
            faq_answers.append(faq['answer'])
            considered.add(faq['answer'][0]['text'])
            c += 1
        with open('export_syn.json', 'w') as fp:
            json.dump(list(json_faqs['synonyms'].keys()), fp, indent=2)

    answer_texts = []
    for i in faq_answers:
        answer_texts.append(i[0]['text'])

    with open(output_file_path, 'w') as fp:
        csv_writer = csv.writer(fp)
        for row in answer_texts:
            if row.startswith('{{'):
                continue
            csv_writer.writerow([row])

    return output_file_path


def tokenize(sentence):
    return word_tokenize(sentence, 'english')


def train_word2Vec(corpus, dim):
    model = Word2Vec(corpus, size=dim, window=5, min_count=1, workers=4)
    model.train(corpus, total_examples=len(corpus), epochs=1000)
    return model

def fetch_synonyms(words, file_name):

    file_name = json_export_to_answers(file_name)
    df = pd.read_csv(file_name, quotechar='"', sep=",")
    df.iloc[:, 0] = df.iloc[:, 0].apply(lambda x: str(x).strip().lower())
    sentences = df.iloc[:, 0].values.tolist()
    sentences = [tokenize(s) for s in tqdm(sentences)]

    model = train_word2Vec(sentences, dim=100)
    wv = model.wv
    print('trained')
    similarities = []
    for word in words:
        try:
            similar = wv.most_similar(word, topn=3)
        except Exception:
            similar = [("", 0)]

        similar_str = "\t".join([(w[0]) for w in similar])
        similarities.append((similar[0][1], word, similar_str))

    similarities.sort(key=lambda x: x[0], reverse=True)

    with open("generated_synonyms.csv", 'w') as fp:
        csv_writer = csv.writer(fp, delimiter=',', quotechar='"')
        for i in similarities:
            csv_writer.writerow([i[1]] + ['/'.join(i[2].split('\t'))])