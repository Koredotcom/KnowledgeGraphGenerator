#add question 
import traceback
import json
import random
import requests
import uuid
from _collections import defaultdict
import string
import nltk
from nltk.corpus import stopwords 
import csv
import argparse
import re
from bs4 import BeautifulSoup
from indentAPI import Indent
from log.Logger import Logger
import CSV_utill as csv_util
from pathlib import Path
from datetime import date
from shutil import copyfile
import os
oa=Logger()
#nltk.download('stopwords')
api=Indent()



def termAdder_json(terms, nouns):
	if len(nouns) <= 2: 
		terms.extend(nouns)
		#reverse the list because we want the primary term at the end 
		terms.reverse() 
		#add to front of the list 
	else: 
		#FOR TIME BEING: just appending the first 2 nouns as terms 
		terms.extend(nouns[:2])
		terms.reverse()

#adding tags : JSON VERSION, with added accommodation for dialog intents 
def tagAdder_json(tags, verbs, adj, dialog=False): 
	

	if dialog:
		if len(adj) == 0: 
			for verb in verbs: 
				tags.append({"name": verb})
		elif len(verbs) ==0: 
			for ad in adj: 
				tags.append({"name": ad})
		elif len(adj) >= 2: 
			for ad in adj[:1]: 
				tags.append({"name": ad})
			for verb in verbs[:0]: 
				tags.append({"name": verb})
		elif len(verbs) >= 2: 
			for ad in adj[:1]: 
				tags.append({"name": ad})
			for verb in verbs[:2]: 
				tags.append({"name": verb})
		else: 
			for ad in adj: 
				tags.append({"name": ad})
			for verb in verbs: 
				tags.append({"name": verb}) 
	else: 
		if len(adj) == 0: 
			tags.extend(verbs)
		elif len(verbs) ==0: 
			tags.extend(adj)
		elif len(adj) >= 2: 
			tags.extend(adj[:1])
			tags.extend(verbs[:0])
		elif len(verbs) >= 2: 
			tags.extend(verbs[:2])
			tags.extend(adj[:1])
		else: 
			tags.extend(adj)
			tags.extend(verbs)


def getAltTagsJson(q, terms, tags): 
	#tokenizing the question, so that we can extract the necessary parts of speech
	temp = nltk.word_tokenize(q.lower())
	temp = nltk.pos_tag(temp)
	#classified verbs in this question (every verbs classification has the first letter as V)
	q_verbs = [pair[0] for pair in temp if pair[1][0] == 'V' and pair[0] not in stopwords.words("english") and pair[0].isalpha()]
	#classified adjective in this question (every adjective classification has the first letter as J)
	q_adj = [pair[0] for pair in temp if pair[1][0] == 'J' and pair[0] not in stopwords.words("english") and  pair[0].isalpha()]


	tagAdder_json(tags, q_verbs, q_adj, True)


def addsynonyms(data):

	synonyms=set()

	for faq in data["faqs"]:
		x=faq["terms"][0].find("/")
		if x>0:
		
			synonyms.add(faq["terms"][0])
		
	synonyms=list(synonyms)
	for synm in synonyms:
		x=synm.split("/")
		# for node in x:
		node=x[0].replace('**','')
		node=node.replace('!!','')

		if node not in data["synonyms"]:
			
			data["synonyms"][node]=x[1:]

def update_generated_synonyms(generated_syn_path,graph_level_synonyms):
	if generated_syn_path:
		try:
			generated_synonyms=read_file_csv(generated_syn_path)
			result=defaultdict(list)
		
			if len(graph_level_synonyms)>0:
				for key in graph_level_synonyms:
					result[key]=graph_level_synonyms[key]
			for row in generated_synonyms:
				if len(row)>1:
					synonyms=[]
					key=row[0]
				for val in row[1].split('/'):
					val = val.strip()
					if val not in synonyms:
						synonyms.append(val)
				if len(synonyms)>1:
					result[key].extend(synonyms)		
			return result
		except Exception as err:
			oa.error(err)
			return graph_level_synonyms
	else:
		return graph_level_synonyms

 
#adding terms 
def termAdder(terms, nouns):
	if len(nouns) <= 2: 
		terms.extend(nouns)
		#reverse the list because we want the primary term at the end 
		terms.reverse() 
		#add to front of the list 
	else: 
		#FOR TIME BEING: just appending the first 2 nouns as terms 
		terms.extend(nouns[:2])
		terms.reverse()

def tagAdder(tags, verbs, adj): 
	#FOR NOW: adding all verbs and adjectives as tags 
	tags.extend(adj)
	tags.extend(verbs)


def questionadder(qaPair, data): 
	"""qaPair is a tuple representing the new qa, 
		where the first element is the question string, 
		and the second element is the answer string 
		ogFile represents the json of the original, fully trained knowledge graph, or graph A
		primaryTerm represents the root node of what is present in the fully trained bot / graph A
	"""
	
	"""setting up the new QA in the KG format. 
		All fields except for given question, answer, 
		bot primary term (root node of KG) and a randomly generated ID 
		have been left blank. 
	"""
	
	new_qa = {}
	new_qa["question"] = qaPair[0]
	new_qa["alternateQuestions"] = []
	new_qa["terms"] = []#[data["nodes"][0]["terms"][0]]
	#new_qa["terms"].append(primaryTerm)
	new_qa["tags"] = []
	new_qa["refid"] = str(uuid.uuid4())
	new_qa["responseType"] = "message"
	new_qa["answer"] = []
	new_qa['answer'].append({
		"text":  qaPair[1], 
		"type":"basic", 
		"channel":"default"
	})
	new_qa["alternateAnswers"] = []

	

	## read the Faq Q and fire the api with question
	## call the indend api to get the score
	## if we get score of more than 80 get the path and add the question to into Graph A
	## under the path
	primaryQuestion=api.callintentAPI(qaPair[0]) #callintendAPI(qaPair[0])
	print("adding ",qaPair[0])
	if primaryQuestion:

		###handling FAQ's : appending the new question to the pre-existing qa's 
		for faq in data["faqs"]:
			if faq["question"]==primaryQuestion:
				for term in faq["terms"]:

					new_qa["terms"].append(term)
					print(new_qa["terms"])
				for tag in faq["tags"]:
					new_qa["tags"].append(tag)
		
		oa.info("Question added the specific path")
		data["faqs"].append(new_qa)

					

		
	else:
		# print("adding ",qaPair[0])
		# temp = nltk.word_tokenize(qaPair[0].lower())
		# temp = nltk.pos_tag(temp)

		# #classified nouns in this question (every noun classification has the first letter as N)
		# q_nouns = [pair[0] for pair in temp if pair[1][0] == 'N' and pair[0] not in stopwords.words("english")]
		# #classified verbs in this question (every verbs classification has the first letter as V)
		# q_verbs = [pair[0] for pair in temp if pair[1][0] == 'V' and pair[0] not in stopwords.words("english")]
		# #classified adjective in this question (every adjective classification has the first letter as J)
		# q_adj = [pair[0] for pair in temp if pair[1][0] == 'J' and pair[0] not in stopwords.words("english")]

		# #adding the terms and tags 
		# termAdder(new_qa["terms"], q_nouns)
		# tagAdder(new_qa["tags"], q_verbs, q_adj)
		# data["faqs"].append(new_qa)
		# oa.info("Question added under root")
		print(data["nodes"][0]["terms"][0])
		AddQuesUnderRoot(data,qaPair,primaryTerm=data["nodes"][0]["terms"][0])


def add_new_faq_csv(args):

	copyfile(args['input_file_path'],args['output_file_path'])
	primary_term=extract_primary_term(args['input_file_path'])

	if '.json' in args['newFaqFile']:
		ques_ans_pair=read_json_file(args['newFaqFile'])
		data=read_file_csv(args['input_file_path'])
		for QandA in ques_ans_pair['faq']:
			qapair=(QandA["question"],QandA["answer"])
			csv_util.questionadder_csv(qapair,primary_term,args['output_file_path'])
		

	elif '.csv' in args['newFaqFile']:
		ques_ans_pair=read_file_csv(args['newFaqFile'])
		
		for QandA in ques_ans_pair[1:]:
			qapair=(QandA[0].strip(),QandA[1].strip())
			csv_util.questionadder_csv(qapair,primary_term,args['output_file_path'])
		
	else:
		oa.debug('please check the args newFaqFile  name should be a JSON or CSV')
		print("please check the args newFaqFile name should be a JSON or CSV ")
	




def add_new_faq_json(data,args):

	ques_ans_pair=list()
	if '.json' in args['newFaqFile']:
		ques_ans_pair=read_json_file(args['newFaqFile'])
		for QandA in ques_ans_pair['faq']:
			qapair=(QandA["question"],QandA["answer"])
			questionadder(qapair,data)

	elif '.csv' in args['newFaqFile']:
		ques_ans_pair=read_file_csv(args['newFaqFile'])
		
		for QandA in ques_ans_pair[1:]:
			qapair=(QandA[0].strip(),QandA[1].strip())
			questionadder(qapair,data)
	else:
		oa.debug('please check the args newFaqFile  name should be a JSON or CSV')
		print("please check the args newFaqFile name should be a JSON or CSV ")
	

	
	if args["syn_file_path"] is not None:
		
		oa.info("Starting update generated synonyms")
		graph_level_synonyms=update_generated_synonyms(args["syn_file_path"],data["synonyms"])
		data["synonyms"]=dict(graph_level_synonyms)
	
	write_json_file(args,data)



	
def read_file_csv(file_path):
	csv_data = list()
	try:
		with open(file_path, 'r', encoding='utf-8') as fp:
			csv_reader = csv.reader(fp)
			for row in csv_reader:
				csv_data.append(row)
	except Exception:
		oa.error(traceback.format_exc())
	finally:
		return csv_data

def write_json_file(args,data):
	try:
		oa.info("writing the data into json output file")
		with open(args["output_file_path"], 'w') as outfile: 
		#extracting all the data as is from our graph A 
			json.dump(data,outfile)
		
	except Exception:
		oa.error(traceback.format_exc())
	

	
def read_json_file(file_path):
	ogFile=file_path
	data=None
	try:
		with open(ogFile, 'r',encoding='utf-8') as infile: 
		#extracting all the data as is from our graph A 
			data = json.load(infile)
	except Exception:
		oa.error(traceback.format_exc())
	finally:
		return data
	
	

def AddQuesUnderRoot(data, qaPair=("Would you like chamomile tea?", "yes"), primaryTerm="test_bot", alternates=False, alt_list=None, resp_type="message"): 

	new_qa = {}
	new_qa["question"] = qaPair[0]
	new_qa["alternateQuestions"] = []

	#term has been defined to include the primaryTerm (root node), initially
	new_qa["terms"] = [primaryTerm]
	new_qa["tags"] = []

	#replace this line below with the uuid 
	new_qa["refId"] = str(uuid.uuid4())#str(random.randint(1, 10000))
	new_qa["responseType"] = resp_type

	if resp_type == "dialog": 
		new_qa["dialogRefId"] = qaPair[1]
	elif resp_type == "message":
		new_qa["answer"] = []
		new_qa['answer'].append({
			"text":  qaPair[1], 
			"type":"basic", 
			"channel":"default"
		})
		new_qa["alternateAnswers"] = []
	

	##

	temp = nltk.word_tokenize(qaPair[0].lower())
	temp = nltk.pos_tag(temp)

	#classified nouns in this question (every noun classification has the first letter as N)
	q_nouns = [pair[0] for pair in temp if pair[1][0] == 'N' and pair[0] not in stopwords.words("english") and pair[0].isalpha()]
	#classified verbs in this question (every verbs classification has the first letter as V)
	q_verbs = [pair[0] for pair in temp if pair[1][0] == 'V' and pair[0] not in stopwords.words("english") and pair[0].isalpha()]
	#classified adjective in this question (every adjective classification has the first letter as J)
	q_adj = [pair[0] for pair in temp if pair[1][0] == 'J' and pair[0] not in stopwords.words("english") and  pair[0].isalpha()]


	#ensuring that nodes for primary questions with alternate questions have words that are present in BOTH primary and 
	#all alternates 
	if alternates: 
		all_alt_words = []
		for q in alt_list: 
			curr_words = q.split()

			#removing punctuation from each word
			curr_words = ["".join(l for l in wd if wd not in string.punctuation) for wd in curr_words]
			all_alt_words.extend(curr_words)
		q_nouns = [noun for noun in q_nouns if noun in all_alt_words]


		termAdder_json(new_qa["terms"], q_nouns)
	else: 
		termAdder_json(new_qa["terms"], q_nouns)
	#adds the tags for the primary question
	tagAdder_json(new_qa["tags"], q_verbs, q_adj)

	#There was an issue with my order, I’d like to contact the seller.

	if alternates: 
		for q in alt_list: 
			new_alt = {}
			new_alt["question"] = q
			new_alt["terms"] = copy.copy(new_qa["terms"])
			new_alt["tags"] = []
			getAltTagsJson(q, new_qa["terms"], new_alt["tags"])

			#adding in each new alternate
			new_qa["alternateQuestions"].append(new_alt)


	print(new_qa["terms"])

	#need to update data["nodes"] --> w/the new terms of the questions 
	curr_nodes = [node["terms"] for node in data["nodes"]]

	i = len(new_qa["terms"])-1
	while i >= 0: 
		#parse through all the terms lists 
		curr = new_qa["terms"][i:]
		print("adding the node",curr) 
		if curr not in curr_nodes:
			
			new_node = {}
			new_node["terms"] = curr 
			new_node["preConditions"] = []
			new_node["contextTags"] = []
			data["nodes"].append(new_node)
		i-=1
		#for the whole length, check that all the incremental term combinations are present
	
	data["faqs"].append(new_qa)

#JSON VERSION
def deleteQ_json(args,question="Do you want chamomile tea?"): 
	data=read_json_file(args["input_file_path"])
	for i in range(0, len(data["faqs"])-1): 
		if data["faqs"][i]["question"] == question: 
			data["faqs"].remove(data["faqs"][i])
	print("deleting question ",question)
	#dumping the edited data (first question removed) back into the json file
	write_json_file(args,data)

#JSON VERSION
def editQ_json(args, question="Do you want chamomile tea?", replacement="What kind of tea do you want?"): 
	#reads in the json file
	data = read_json_file(args["input_file_path"])
	#saves the answer of the prior question, and removes the current question from the json
	ans = ""
	primaryTerm = ""
	for i in range(0, len(data["faqs"])-1):


		if data["faqs"][i]["question"] == question.strip(): 
			ans = data["faqs"][i]["answer"][0]["text"]
			#reversing the list, then getting what's at the front (last term in list is the primary term )
			data["faqs"][i]["terms"].reverse()
			#primaryTerm = data["faqs"][i]["terms"][0]
			data["faqs"].remove(data["faqs"][i])
			questionadder((replacement, ans),data)

			write_json_file(args,data)
			break



def extract_primary_term(file_name):
	data=read_file_csv(file_name)
	print(file_name)
	header = ['Node', 'Que ID', 'nodepath', 'Tag', 'precondition', 'outputcontext', 'Traits', 'enableContext'] 
	flag=0
	primaryTerm=None
	for row in data:
		if row==header:
			flag=1
			continue
		if flag:
			temp=row[2]
			for i in temp.split(','):
				primaryTerm=i
				break
			#a,b=temp.split(',')
			#primaryTerm=a
			break
	
	oa.info("Selecting "+primaryTerm+"as the primary term")
	print("Selecting the primary term as",primaryTerm)
	if not flag:
		print("Please check the input csv file")
		return 0
	else:
		return primaryTerm

	
def backup_inputKG(input_file_name):
	today = date.today()
	backup_file=str(today)+'-'+input_file_name
	if not os.path.isfile('backup/'+backup_file):
		copyfile(input_file_name,'backup/'+backup_file)
		oa.info("backup of file complete at backup/"+backup_file)
	else:
		oa.info("backup of file already exists at: backup/"+backup_file)

def cleaninput(text):


    soup = BeautifulSoup(text,features="lxml")

    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.decompose()    # rip it out

    # get text
    text = soup.get_text()

    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)
    for k in text.split("\n"):
        text=re.sub(r"[^-_'!?a-zA-Z0-9]+", ' ', k)
    

    return text

	



if __name__=="__main__":

	parser=argparse.ArgumentParser()
	parser.add_argument('--file_path',help='path for the input json/csv')
	#parser.add_argument('--type', help='types supported are faq_json, csv',default='json')
	parser.add_argument('--operation', help='operation are add,edit and delete a question',default='add')
	parser.add_argument('--newFaqFile',help='the file of new faq',default=None)
	#parser.add_argument('--newFaqFile_type',help='the type new faq file',default='json')
	parser.add_argument('--synonyms_file_path', help='path to synonym file that needs to be included in output export',
                         default=None)

	_input_arguments = parser.parse_args()
	


	## controller function

	args=dict()
	args['input_file_path']=_input_arguments.file_path
	args['syn_file_path']=_input_arguments.synonyms_file_path
	#args['type']=_input_arguments.type
	args['operation']=_input_arguments.operation
	args['newFaqFile']=_input_arguments.newFaqFile
	#args['new_ques_file_type']=_input_arguments.newFaqFile_type




	oa.info("Started the Execution of KG Util")
	if not args['input_file_path']=='':
		backup_inputKG(args['input_file_path'])
	else:
		print("check the input args file")

	if '.json' in args['input_file_path']:

		args['output_file_path']='output_file.json'

		if args['operation']=='edit':
			question=cleaninput(str(input("Enter a quesiton to edit: ")))
			replacement=cleaninput(str(input("\n Enter the replacement question: ")))


			if question=='' or replacement=='':
				print("Check the entered quesiton")
			else:
				editQ_json(args,question.strip(),replacement.strip())
				oa.info("Question: "+question+" edited successfuly")

		if args['operation']=='delete':
			question=cleaninput(str(input("Enter the question to delete:")))
			if question=='':
				print("Check the entered quesiton")
			else:
				deleteQ_json(args,question.strip())
		
		if args['operation']=='add':
			data=None
			data=read_json_file(args['input_file_path'])
			add_new_faq_json(data,args)

	elif '.csv' in args['input_file_path']:
		args['output_file_path']='output_file.csv'

		if args['operation']=='edit':
			question=cleaninput(str(input("Enter a quesiton to edit: ")))
			replacement=cleaninput(str(input("\n Enter the replacement question: ")))
			if question=='' or replacement=='':
				print("Check the entered quesiton")
			else:
				print("searching the question as\t",question)
				print("putting the replacement as\t",replacement)
				print("\n")
				csv_util.editQ_csv(question,replacement,args['input_file_path'],args['output_file_path'])
				oa.info("Question: "+question+" edited successfuly")

		if args['operation']=='delete':
			question=cleaninput(str(input("Enter the question to delete:")))
			if question=='':
				print("Check the entered quesiton")
			else:
				print("searching the question as \t",question)
				print("\n")
				csv_util.deleteQ_csv(question,args['input_file_path'],args['output_file_path'])

		
		if args['operation']=='add':
			add_new_faq_csv(args)





	else:
		print('please check the args input_file_path name should be a JSON or CSV')
		

	
	

	

	
	








