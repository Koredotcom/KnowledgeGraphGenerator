import argparse
import traceback

from analyzer.ontology_analyzer import OntologyAnalyzer
#from analyzer.ontology_analyzer import OntologyclAnalyzer
from log.Logger import Logger
from request_type.CSVExportParser import CSVExportParser
from request_type.CSVParser import CSVParser as csvParser
from request_type.JSONExportParser import JSONExportParser as jsonParser
from response_type.JSONGenerator import JSONGenerator
from strategy.NGramStrategy import GramBasedGenerator
from graph_optmiser.Optmiser import Optimiser

logger = Logger()
analyzer = OntologyAnalyzer()
optimiser = Optimiser()


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
        tag_term_map = graph_generator().generate_graph(response_payload.get('question_map'),
                                                        response_payload.get('stop_words'))
        response_payload['tag_term_map'] = tag_term_map
## get terms and tags
##
        response_payload = optimiser.optimise_graph(response_payload)
        response_generator = self.get_response_generator()
        response = response_generator.create_response(response_payload)
        response_generator.write_response_to_file(response, args.get('output_file_path'))
        if len(response.get('faqs', [])) > 0:
            print('Analyzing generated graph...')
            try:
                analyzer_args = {'language': args.get('lang_code'), 'input_file_path': args.get('output_file_path')}
                analyzer.run_diagnostics(analyzer_args)
            except:
                print('Error in analyzing graph !!!, go through log/auto_kg.log for detailed report')
                logger.error(traceback.format_exc())
        else:
            print('Nothing to analyze...')
        print('Graph generation completed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', help='path for input json file')
    parser.add_argument('--language', help='language in which questions present', default='en')
    parser.add_argument('--v', help='to get detailed console logging', default=False)
    parser.add_argument('--type', help='types supported are faq_json, csv')
    parser.add_argument('--synonyms_file_path', help='path to synonym file that needs to be included in output export',
                        default=None)
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
    args['syn_file_path'] = _input_arguments.synonyms_file_path
    print_verbose('startup check initialised')
    ontology_generator = KnowledgeGraphGenerator()
    ontology_generator.generate_graph(args)
