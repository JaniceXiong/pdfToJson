import sys
import os
import io
import json
import argparse
import time
import concurrent.futures
from client import ApiClient
import ntpath
import requests
from xmlToJson import XmlToJson
import pickle
import logging

#一个一个文件夹处理pdf，将json也按文件夹保存
#再统一存到一个json中

'''
This version uses the standard ProcessPoolExecutor for parallelizing the concurrent calls to the GROBID services. 
Given the limits of ThreadPoolExecutor (input stored in memory, blocking Executor.map until the whole input
is acquired), it works with batches of PDF of a size indicated in the config.json file (default is 1000 entries). 
We are moving from first batch to the second one only when the first is entirely processed - which means it is
slightly sub-optimal, but should scale better. However acquiring a list of million of files in directories would
require something scalable too, which is not implemented for the moment.   
'''
class grobid_client(ApiClient):

    def __init__(self, config_path='./config.json'):
        self.config = None
        self._load_config(config_path)
        self.tool = XmlToJson()

    def _load_config(self, path='./config.json'):
        """
        Load the json configuration 
        """
        config_json = open(path).read()
        self.config = json.loads(config_json)

        # test if the server is up and running...
        the_url = 'http://'+self.config['grobid_server']
        if len(self.config['grobid_port'])>0:
            the_url += ":"+self.config['grobid_port']
        the_url += "/api/isalive"
        r = requests.get(the_url)
        status = r.status_code

        if status != 200:
            print('GROBID server does not appear up and running ' + str(status))
        else:
            print("GROBID server is up and running")

    def process(self, input, output, outputJsons_path, n, service, generateIDs, consolidate_header, consolidate_citations, force, teiCoordinates):
        batch_size_pdf = self.config['batch_size']
        pdf_files = []

        for (dirpath, dirnames, filenames) in os.walk(input):
            for filename in filenames:
                if filename.endswith('.pdf') or filename.endswith('.PDF'): 
                    pdf_files.append(os.sep.join([dirpath, filename]))

                    if len(pdf_files) == batch_size_pdf:
                        self.process_batch(pdf_files, output, n, service, generateIDs, consolidate_header, consolidate_citations, force, teiCoordinates)
                        pdf_files = []

        # last batch
        if len(pdf_files) > 0:
            self.process_batch(pdf_files, output, n, service, generateIDs, consolidate_header, consolidate_citations, force, teiCoordinates)

    def process_batch(self, pdf_files, output, n, service, generateIDs, consolidate_header, consolidate_citations, force, teiCoordinates):
        print(len(pdf_files), "PDF files to process")
        #with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
        with concurrent.futures.ProcessPoolExecutor(max_workers=n) as executor:
            for pdf_file in pdf_files:
                executor.submit(self.process_pdf, pdf_file, output, service, generateIDs, consolidate_header, consolidate_citations, force, teiCoordinates)

    def process_pdf(self, pdf_file, output, service, generateIDs, consolidate_header, consolidate_citations, force, teiCoordinates):
        # check if TEI file is already produced 
        # we use ntpath here to be sure it will work on Windows too
        pdf_file_name = ntpath.basename(pdf_file)
        if output is not None:
            filename = os.path.join(output, os.path.splitext(pdf_file_name)[0] + '.json')
        else:
            filename = os.path.join(ntpath.dirname(pdf_file), os.path.splitext(pdf_file_name)[0] + '.json')

        if not force and os.path.isfile(filename):
            print(filename, "already exist, skipping... (use --force to reprocess pdf input files)")
            return

        print(pdf_file)
        files = {
            'input': (
                pdf_file,
                open(pdf_file, 'rb'),
                'application/pdf',
                {'Expires': '0'}
            )
        }
        
        the_url = 'http://'+self.config['grobid_server']
        if len(self.config['grobid_port'])>0:
            the_url += ":"+self.config['grobid_port']
        the_url += "/api/"+service

        # set the GROBID parameters
        the_data = {}
        if generateIDs:
            the_data['generateIDs'] = '1'
        if consolidate_header:
            the_data['consolidateHeader'] = '1'
        if consolidate_citations:
            the_data['consolidateCitations'] = '1'   
        if teiCoordinates:
            the_data['teiCoordinates'] = self.config['coordinates'] 

        res, status = self.post(
            url=the_url,
            files=files,
            data=the_data,
            headers={'Accept': 'text/plain'}
        )

        if status == 503:
            time.sleep(self.config['sleep_time'])
            return self.process_pdf(pdf_file, output)
        elif status != 200:
            print('Processing failed with error ' + str(status))
        else:
            # writing JSON file
            try:
            
                json_data = self.tool.run(res.text)
                
                #保存单个json文件
                with io.open(filename,'w',encoding='utf8') as json_file:
                    json.dump(json_data,json_file)
                
                print("Saving json file %s" % filename)
                
            except Exception as e:  
               logger.info("Generating resulting JSON file %s failed" % filename)
               logger.info("Error is %s" % e)
    
def saveOneJson(input, output,outputJsons_path):
    all_data = {}
    for (dirpath, dirnames, filenames) in os.walk(output):
            for filename in filenames:
                if filename.endswith('.json') or filename.endswith('.JSON'):
                    json_path = os.sep.join([dirpath, filename]) 
                    with open(json_path,'r',encoding='utf-8') as json_f:
                        json_data = json.load(json_f)
                    title = json_data['Title']
                    all_data[title] = json_data
    
    print("Generating %d json data from %s" % (len(all_data),input))
    with open(outputJsons_path,'w',encoding='utf-8') as all_f:
        json.dump(all_data,all_f)
    
#python pdfToJson.py --input C:\Users\xjw\Desktop\Task\pdf_test --output C:\Users\xjw\Desktop\Task\json_test --outputJsons ./all_data_test.json --log ./log.txt processFulltextDocument
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Client for GROBID services")
    parser.add_argument("service", help="one of [processFulltextDocument, processHeaderDocument, processReferences]")
    parser.add_argument("--input", default=None, help="path to the directory containing PDF to process") 
    parser.add_argument("--output", default=None, help="path to the directory where to put the results (optional)") 
    parser.add_argument("--outputJsons", default=None, help="path to the json file containing all results")
    parser.add_argument("--log", default=None, help="path to the log file")
    parser.add_argument("--config", default="./config.json", help="path to the config file, default is ./config.json") 
    parser.add_argument("--n", default=10, help="concurrency for service usage") 
    parser.add_argument("--generateIDs", action='store_true', help="generate random xml:id to textual XML elements of the result files") 
    parser.add_argument("--consolidate_header", action='store_true', help="call GROBID with consolidation of the metadata extracted from the header") 
    parser.add_argument("--consolidate_citations", action='store_true', help="call GROBID with consolidation of the extracted bibliographical references") 
    parser.add_argument("--force", action='store_true', help="force re-processing pdf input files when tei output files already exist")
    parser.add_argument("--teiCoordinates", action='store_true', help="add the original PDF coordinates (bounding boxes) to the extracted elements")

    args = parser.parse_args()

    input_path = args.input
    config_path = args.config
    output_path = args.output
    outputJsons_path = args.outputJsons
    log_path = args.log

    logger = logging.getLogger(__name__)
    logger.setLevel(level = logging.INFO)
    handler = logging.FileHandler(log_path)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    
    logger.addHandler(handler)
    logger.addHandler(console)
    
    n =10
    if args.n is not None:
        try:
            n = int(args.n)
        except ValueError:
            print("Invalid concurrency parameter n:", n, "n = 10 will be used by default")
            pass

    # if output path does not exist, we create it
    if output_path is not None and not os.path.isdir(output_path):
        try:  
            print("output directory does not exist but will be created:", output_path)
            os.makedirs(output_path)
        except OSError:  
            print ("Creation of the directory %s failed" % output_path)
        else:  
            print ("Successfully created the directory %s" % output_path)

    service = args.service
    generateIDs = args.generateIDs
    consolidate_header = args.consolidate_header
    consolidate_citations = args.consolidate_citations
    force = args.force
    teiCoordinates = args.teiCoordinates

    client = grobid_client(config_path=config_path)

    start_time = time.time()

    client.process(input_path, output_path, outputJsons_path, n, service, generateIDs, consolidate_header, consolidate_citations, force, teiCoordinates)

    runtime = round(time.time() - start_time, 3)
    print("runtime: %s seconds " % (runtime))
    
    saveOneJson(input_path,output_path,outputJsons_path)
