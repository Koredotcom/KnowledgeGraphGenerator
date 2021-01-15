#add question 
import json
import random
import string
import nltk
from nltk.corpus import stopwords 
import csv 
import copy
import pandas as pd
import uuid
from indentAPI import Indent
api=Indent()
from log.Logger import Logger
oa=Logger()

def getAltTagsCsv(q, terms, tags): 
	#tokenizing the question, so that we can extract the necessary parts of speech
	temp = nltk.word_tokenize(q.lower())
	temp = nltk.pos_tag(temp)

	#classified verbs in this question (every verbs classification has the first letter as V)
	q_verbs = [pair[0] for pair in temp if pair[1][0] == 'V' and pair[0] not in stopwords.words("english") and pair[0].isalpha()]
	#classified adjective in this question (every adjective classification has the first letter as J)
	q_adj = [pair[0] for pair in temp if pair[1][0] == 'J' and pair[0] not in stopwords.words("english") and  pair[0].isalpha()]

	tagAdder_csv(q_verbs, q_adj)


def termAdder_csv(nouns):
	if len(nouns) <=2: 
		terms = ",".join(nouns)
	else: 
		terms = ",".join(nouns[:2])
	return terms

def tagAdder_csv(verbs, adj): 
	totals = verbs + adj
	if len(totals) <=3: 
		tags = ",".join(totals)
	else: 
		tags = ",".join(totals[:3])
	return tags

	




#CSV VERSION
def deleteQ_csv(question, input_file, output_csv): 
	#built on the assumption that to completely delete traces of the question, delete all rows with its question ID
	#finding the question and collecting its ID 
	que_ID = None
	oa.debug("delete question CSV started")
	with open(input_file, mode='r',encoding='utf-8') as readfile:
		csvFile = csv.reader(readfile)
		#need to skip lines that include 'Que ID' --> a marker for the titles row 
		for line in csvFile: 
			if 'Que ID' not in line and question in line:
				#assuming that the second element will always be the question id 
				print(line)
				que_ID = line[1]
				break 

	if que_ID is not None:
		
		oa.debug("Deleting question found")
		#getting all the CSV contents
		data = None
		with open(input_file, newline='',encoding='utf-8') as f: 
			reader = csv.reader(f)
			data=list(reader)
		
		#including only rows that don't include the question ID 
		#later replace dummy test.csv w file and see what happens
		oa.debug("writing the new file")
		with open(output_csv, mode='w',encoding='utf-8',newline='') as writefile: 
			csvWriter = csv.writer(writefile)
			for line in data: 
				if que_ID not in line: 
					csvWriter.writerow(line)
	else:
		print("question not found")
		oa.debug("question not found")



		

#CSV VERSION
def editQ_csv(question, replacement,input_file, output_csv): 
	que_ID = None
	primaryTerm = ""
	ans = ""
	oa.debug("searching the question")
	#get the primary term and answer, then delete the question
	with open(input_file, mode='r',encoding='utf-8') as readfile: 
		csvFile = csv.reader(readfile)
		#need to skip lines that include 'Que ID' --> a marker for the titles row 
		for line in csvFile: 
			if 'Que ID' not in line and question in line:
				#assuming that the second element will always be the question id 
				que_ID = line[1]
				ans = line[6]
				terms = line[2].split(",")
				primaryTerm = terms[0]
				break 

	if que_ID is not None:
	#remove the questions
		deleteQ_csv(question, input_file,output_csv)
	#add in the new question with its replacement
		oa.debug("adding edited question")
		questionadder_csv((replacement, ans),primaryTerm,output_csv)
		
	else:
		print("no question found")
		

def read_input_csv(input_file):
	#getting csv data
	data = list()
	with open(input_file, newline='',encoding='utf-8') as f: 
		reader = csv.reader(f)
		for row in reader:
			data.append(row)
	
	

def write_input_csv(output_csv):
	with open(output_csv, mode='w',encoding='utf-8') as writefile: 
		csvWriter = csv.writer(writefile)
		csvWriter.writerows(op_data)

#CSV VERSION

"""
NOTES FOR CSV VERSION: 
- if a dialog type question is added instead of a typical q/a pair part of an FAQ, then the second element of the qaPair should be the intent ID
"""
def questionadder_csv(qaPair,primaryTerm,output_csv,alternates = False, alt_list=None):
	oa.debug("adding question the started")
	data = None
	with open(output_csv, newline='',encoding='utf-8') as f: 
		reader = csv.reader(f)
		data=list(reader)
	
	
	primaryQuestion=api.callintentAPI(qaPair[0])


	print("adding ",qaPair[0])
	q_ID=""
	path=""
	tags=""
	tags_list=None
	if primaryQuestion:
		for line in data: 
			if 'Que ID' not in line and primaryQuestion in line:
				#assuming that the second element will always be the question id 
				q_ID = line[1]
				path = line[2]
				tags = line[5]
				tags_list = tags.split(",")
				break
		
	else:
		oa.debug("creating tag and terms")
		#temp becomes an array of tuples, where the second element is the part of speech as tagged by nltk
		temp = nltk.word_tokenize(qaPair[0].lower())
		temp = nltk.pos_tag(temp)

		#classified nouns in this question (every noun classification has the first letter as N)
		q_nouns = [pair[0] for pair in temp if pair[1][0] == 'N' and pair[0] not in stopwords.words("english") and pair[0].isalpha()]
		#classified verbs in this question (every verbs classification has the first letter as V)
		q_verbs = [pair[0] for pair in temp if pair[1][0] == 'V' and pair[0] not in stopwords.words("english") and pair[0].isalpha()]
		#classified adjective in this question (every adjective classification has the first letter as J)
		q_adj = [pair[0] for pair in temp if pair[1][0] == 'J' and pair[0] not in stopwords.words("english") and  pair[0].isalpha()]


		q_ID = str(uuid.uuid4())##str(random.randint(1, 10000)) #REPLACE W UUID
		path = primaryTerm + "," + termAdder_csv(q_nouns)
		tags = tagAdder_csv(q_verbs, q_adj)
		tags_list = tags.split(",")
		

	#write back to the file with the new question added
	#set the format for the questions

	#building off of the assumption that the sections will always be separated by the same header lines
	header1 = ['Faq', 'Que ID', 'Path', 'Primary Question', 'Alternate Question', 'Tags', 'Answer', 'Extended Answer-1', 'Extended Answer-2']
	header2 = ['Node', 'Que ID', 'nodepath', 'Tag', 'precondition', 'outputcontext', 'Traits', 'enableContext']
	header3 = ["Synonyms", "Phrase", "Synonyms"]


	header1_sec = ['', q_ID, path, qaPair[0], '', tags, qaPair[1], '', ''] 
	header2_sec_path = ['', '', path, 'N', '', '', '', "false"]
	
	alt_header_1 = []
	if alternates: 
		oa.debug("alternates found ")
		for q in alt_list: 
			#get the tags for that question
			tags = getAltTagsCsv(q, path, tags_list)
			header1_sec = ['', q_ID, path, '', q, tags, '', '', '']
			alt_header_1.append(header1_sec)

	if alternates: 
		#add all the alternates after the primary question 
		with open(output_csv, mode='w',encoding='utf-8') as writefile: 
			csvWriter = csv.writer(writefile,quoting=csv.QUOTE_NONNUMERIC)
			for line in data: 
				if line != []: 
					if line == header1:
						csvWriter.writerow(line)
						for head in alt_header_1: 
							csvWriter.writerow(head)
						csvWriter.writerow(header1_sec)
					elif line == header2: 
						csvWriter.writerow(line)
						if header2_sec_path not in data:
							csvWriter.writerow(header2_sec_path)
					elif line == header3: 
						for tag in tags_list:
							header2_sec_tag = ['', q_ID, tag, "Y", '', '', '', '']
							csvWriter.writerow(header2_sec_tag)
					else: 
						csvWriter.writerow(line)
	else: 
		oa.debug("appending the question at the location ")
		for line in data: 
			if line != []: 
				if line == header1:
					if header1_sec not in data:
						data.insert(data.index(line)+1,header1_sec)
				elif line == header2: 			
					if header2_sec_path not in data:
						data.insert(data.index(line)+1,header2_sec_path)				
				elif line == header3: 
					for tag in tags_list:
						header2_sec_tag = ['', q_ID, tag, "Y", '', '', '', '']
						if header2_sec_tag not in data:
							data.insert(data.index(line)+1,header2_sec_tag)
			
	
	if not alternates:
		oa.debug("writing the new output file ")
		with open(output_csv, mode='w',encoding='utf-8',newline='') as writefile: 
			csvWriter = csv.writer(writefile,quoting=csv.QUOTE_NONNUMERIC)
			csvWriter.writerows(data)
		



	

