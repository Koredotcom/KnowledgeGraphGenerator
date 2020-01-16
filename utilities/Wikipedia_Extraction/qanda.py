import csv
import re
import pywikibot

site = pywikibot.Site('en', 'wikipedia')  # The site we want to run our bot on
page = pywikibot.Page(site, 'Chennai Public School')

regex_heading=r"^==.*==$"

def is_question(text):
    return re.search(regex_heading,text)
    
split_page = page.text.split("\n")

with open('../Qanda.csv', 'w') as file:
    writer = csv.writer(file)
    writer.writerow(["Question", "answer"])
    question=[]
    answer=[]
    QnA_pairs = []
    for line_id in range(0, len(split_page)):
        line = split_page[line_id]
        if is_question(line):
            question = line
            QnA_pairs.append([question.strip('=='), answer])
            answer = []
        else:
            answer.append(line)
        if line_id == len(split_page) - 1:
            QnA_pairs.append([question.strip('=='), answer])
    writer.writerows(QnA_pairs)
    
