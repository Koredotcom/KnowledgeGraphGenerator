from log.Logger import Logger
from request_type.JSONExportParser import JSONExportParser as jsonParser
from request_type.CSVParser import CSVParser as csvParser
from request_type.CSVExportParser import CSVExportParser
from graph_generation_strategy.GramBasedGeneration import GramBasedGenerator
from response_type.JSONGenerator import JSONGenerator
import argparse

logger = Logger()


class KnowledgeGraphGenerator(object):
    def __init__(self):
        pass

    @staticmethod
    def get_input_parser(request_type):
        if request_type == 'json_export':
            return jsonParser
        elif request_type == 'csv':
            return csvParser
        elif request_type == 'csv_export':
            return CSVExportParser

    @staticmethod
    def get_graph_generator(generator_type='gram_based'):
        if generator_type == 'gram_based':
            return GramBasedGenerator

    @staticmethod
    def get_response_generator(response_type='json'):
        if response_type == 'json':
            return JSONGenerator()

    def generate_graph(self, args):
        input_parser = self.get_input_parser(args.get('request_type'))
        print_verbose('identified input type and initiated parsing...')
        response_payload = input_parser(args).parse()

        graph_generator = self.get_graph_generator()
        tag_term_map = graph_generator().generate_graph(response_payload.get('question_map'), response_payload.get('stop_words'))
        response_payload['tag_term_map'] = tag_term_map

        response_generator = self.get_response_generator()
        response = response_generator.create_response(response_payload)
        response_generator.write_response_to_file(response, args.get('output_file_path'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', help='path for input json file')
    parser.add_argument('--language', help='language in which questions present', default='en')
    parser.add_argument('--v', help='to get detailed console logging', default=False)
    parser.add_argument('--type', help='types supported are faq_json, csv')
    _input_arguments = parser.parse_args()


    def print_verbose(statement):
        if args.get('verbose', False):
            print(statement)

    args = dict()
    startup_checklist = list()
    args['output_file_path'] = 'ao_output.json'
    args['lang_code'] = _input_arguments.language
    args['verbose'] = _input_arguments.v
    args['input_file_path'] = _input_arguments.file_path
    args['request_type'] = _input_arguments.type
    print_verbose('startup check initialised')
    ontology_generator = KnowledgeGraphGenerator()
    ontology_generator.generate_graph(args)
