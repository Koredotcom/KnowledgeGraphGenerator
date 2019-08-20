from log.Logger import Logger
from request_type.JSONExportParser import JSONInputParser as jsonParser
from request_type.CSVParser import CSVInputParser as csvParser
from request_type.CSVExportParser import CSVExportParser
import argparse
import ntpath

logger = Logger()


class CreateGenerator(object):
    def __init__(self):
        pass

    def get_payload_parser(self, request_type):
        if request_type == 'json_export':
            return jsonParser
        elif request_type == 'csv':
            return csvParser
        elif request_type == 'csv_export':
            return CSVExportParser

    def generate_graph(self, args):
        graph_generator = self.get_payload_parser(args.get('request_type'))
        print_verbose('identified input type and initiated parsing...')
        graph_generator(args).parse_and_generate()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', help='path for input json file')
    parser.add_argument('--language', help='language in which questions present', default='en')
    parser.add_argument('--v', help='to get detailed console logging', default=False)
    parser.add_argument('--type', help='types supported are faq_json, csv')
    _input_arguments = parser.parse_args()


    def path_leaf(path):
        head, tail = ntpath.split(path)
        return tail or ntpath.basename(head)

    def print_verbose(statement):
        if args.get('verbose', False):
            print(statement)

    args = dict()
    startup_checklist = list()
    _file_name = path_leaf(_input_arguments.file_path)
    args['output_file_path'] = 'ao_output.json'
    args['lang_code'] = _input_arguments.language
    args['verbose'] = _input_arguments.v
    args['input_file_path'] = _input_arguments.file_path
    args['request_type'] = _input_arguments.type
    print_verbose('startup check initialised')
    ontology_generator = CreateGenerator()
    ontology_generator.generate_graph(args)
