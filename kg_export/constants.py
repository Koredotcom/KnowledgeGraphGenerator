DEFAULT_CSV_FILE_PATH = 'kg_export/export.csv'
OUTPUT_JSON_FILE_PATH = 'kg_export/KnowledgeGraph_export.json'

""" All the delimiters used by csv and json formats """
TRAIT_DELIMITER = ':'
SYNONYM_DELIMITER = '/'
DEFAULT_DELIMITER = ','
TRAIT_KEY_DELIMITER = '!@#'

''' All the identifiers to recognize particular items in FAQ '''
TEXT_IDENTIFIER = 'SYS_TEXT'
DIALOG_IDENTIFIER = 'SYS_INTENT'
CHANNEL_IDENTIFIER = 'SYS_CHANNEL'
SCRIPT_IDENTIFIER = 'SYS_SCRIPT'
NODE_IDENTIFIERS = ['**', '!!']

'''All the headers used in csv '''
FAQ_HEADER = ['Faq', 'QuesId', 'Path', 'Primary Question', 'Alternate Question', 'Tags', 'Answer', 'Extended Answer-1', 'Extended Answer-2']
NODE_HEADER = ['Node', 'QuesId', 'nodepath', 'Tag', 'PreCondition', 'Output Context', 'Traits']
SYNONYMS_HEADER = ['Synonyms', '', 'phrase', 'Synonyms']
KG_PARAMS_HEADER = ['Kg params', '', 'language', 'Stopwords']
TRAIT_GROUP_HEADER = ['Traits', '', 'lang', 'GroupName', 'MatchStrategy', 'ScoreThreshold', 'TraitName', 'Training Data']

''' column numbers for sections used in csv '''
SECTION_DELIMITING_COUNT = 2
QUES_ID_COL_NO = 1
TERM_PATH_COL_NO = 2
PRIMARY_QUES_COL_NO = 3
ALT_QUES_COL_NO = 4
TAG_PATH_COL_NO = 5
ANS_COL_NO = 6
MIN_COL_COUNT = 20

TERM_PRECON_INDEX = 4
TERM_CONTEXT_INDEX = 5
TERM_TRAIT_INDEX = 6
TERM_CONCEPT_INDEX = 7
REF_ID_INDEX = 1
QUESTION_INDEX = 3

SYNONYM_PHRASE_INDEX = 2
SYNONYM_VALUE_INDEX = 3
KG_PARAM_LANG_INDEX = 2
KG_PARAM_STOPWORDS_INDEX = 3

VALID_SECTIONS = ['faq', 'node', 'synonyms', 'kg params', 'traits']
