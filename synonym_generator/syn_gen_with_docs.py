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


def fetch_synonyms(words, file_name, zip_mode = False):

    temp_dir = 'temp_dir'
    
    if zip_mode:
        merged_pdf = 'merged.pdf'
        with ZipFile(file_name, 'r') as zip: 
            zip.printdir() 
            zip.extractall(temp_dir) 
            print('Extracted ZIP') 
        merger = PdfFileMerger()

        pdfs = [os.path.join(temp_dir, f) for f in listdir(temp_dir) if isfile(join(temp_dir, f))]
        for pdf in pdfs:
            merger.append(pdf)

        merger.write(merged_pdf)
        merger.close()
        file_name = merged_pdf

    sentences = sentenzie_document(file_name)
    sentences = [tokenize(s) for s in tqdm(sentences)]
    model = train_word2Vec(sentences, dim=100)
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

    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)