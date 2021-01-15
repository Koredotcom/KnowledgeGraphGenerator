import argparse
import traceback
import sys
import os
from os import path
sys.path.append(str(os.getcwd())+'/diagnostic')
from ontology_utilities.OntologyAnalyzer import OntologyAnalyzer as af
from anytree.util import commonancestors
from analyzer.ontology_analyzer import OntologyAnalyzer
from anytree import Node, RenderTree, PreOrderIter

analyzer = OntologyAnalyzer()

def generate_csv_report(args):

    args['language'] ="en"
    root_node, parent_faq_map, parent_tags_map = analyzer.run_diagnostics(args)
    tree_traversal = [node for node in PreOrderIter(root_node)]
    myonology=af()
    response=myonology.run_diagnostics(root_node,parent_faq_map,parent_tags_map)
    analyzer.generate_csv_report(response,"csvreport.csv")





if __name__ == "__main__":

    args = dict()
    parser=argparse.ArgumentParser()
    parser.add_argument('--file_path')
    _input_arguments = parser.parse_args()
    args['input_file_path'] =_input_arguments.file_path
    generate_csv_report(args)
      
   
    

