import argparse
from kg_export.json_to_csv import JsonToCsv
from kg_export.csv_to_json import CsvToJson
from kg_export.constants import DEFAULT_CSV_FILE_PATH

def validate_file(file_type):
    pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', help='path for input json file')
    parser.add_argument('--type', help='types supported are json_to_csv and csv_to_json')
    input_arguments = parser.parse_args()
    args = dict()
    args['request_type'] = input_arguments.type
    args['input_file_path'] = input_arguments.file_path if input_arguments.file_path else DEFAULT_CSV_FILE_PATH
    if args.get('request_type', '') == 'json_to_csv':
        parser = JsonToCsv()
        parser.parse(args['input_file_path'])
    elif args.get('request_type', '') == 'csv_to_json':
        parser = CsvToJson()
        parser.parse(args['input_file_path'])
