ontology_analyzer = {
    "QUESTIONS_AT_ROOT_LIMIT": 0,
    "NUMBER_OF_QUESTIONS_AT_ROOT_THRESHOLD": 50,
    "PATH_COVERAGE": 50
}

log = {
    "FORMAT_STRING": "[%(asctime)s] p%(process)s %(levelname)s - %(message)s {%(pathname)s:%(lineno)d}",
    "SERVER_FORMAT_STRING": "[%(asctime)s] %(message)s",
    "ONTOLOGY_ANALYZER_LOG": "log/auto_kg.log",
    "DEBUG_LOG_LEVEL": "ERROR",
    "SERVER_LOG_LEVEL": "INFO"
}

""" All the delimiters used by json format """
TRAIT_DELIMITER = ':'
SYNONYM_DELIMITER = '/'

''' All the identifiers to recognize particular items in FAQ '''
NODE_IDENTIFIERS = ['**', '!!']
