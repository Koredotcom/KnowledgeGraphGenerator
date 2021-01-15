import csv
from nltk import word_tokenize
from tqdm import tqdm
from gensim.models import Word2Vec
import os
from zipfile import ZipFile 
import os
import shutil
from PyPDF2 import PdfFileMerger
from os import listdir
from os.path import isfile, join
import gensim 
from gensim.models import Word2Vec 
import sys

def sentenzie_document(file_name):
    os.system('pdftotext ' + file_name)
    textfile = file_name.split('.')[0] + '.txt'
    f = open(textfile, 'r')
    lines = f.readlines()
    f.close()
    return lines

def tokenize(sentence):
    return word_tokenize(sentence, 'english')


def train_word2Vec(corpus, dim):
    model = Word2Vec(corpus, size=dim, window=5, min_count=1, workers=4)
    model.train(corpus, total_examples=len(corpus), epochs=1000)
    return model


def fetch_synonyms(words, file_name, pretrained_model, zip_mode = False):
    model = gensim.models.KeyedVectors.load_word2vec_format(pretrained_model, binary=True)#, norm_only=True)
    wv = model.wv

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