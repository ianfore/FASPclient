#  IMPORTS
#from google.cloud import bigquery
import sys, getopt
import os.path
import json
import datetime
import subprocess 

# a utility 
from FASPLogger import FASPLogger
from DemoCredits import Creditor

# The implementations we're using
from Gen3DRSClient import crdcDRSClient
from Gen3DRSClient import bdcDRSClient
from GCPLSsamtools import GCPLSsamtools
from BigQuerySearchClient import BigQuerySearchClient



def main(argv):

	# create a creditor to credit the services being called
	creditor = Creditor.creditorFactory()
	
	# Step 1 - Discovery
	# query for relevant DRS objects
	searchClient = BigQuerySearchClient()

	crdcquery = """
     	SELECT 'case_'||associated_entities__case_gdc_id , 'crdc:'||file_id
		FROM `isb-cgc.GDC_metadata.rel24_fileData_active` 
		where data_format = 'BAM' 
		and project_disease_type = 'Breast Invasive Carcinoma'
		limit 3"""
		
	bdcquery = """
  		SELECT SUBJECT_ID, 'bdc:'||read_drs_id
  		FROM `isbcgc-216220.COPDGene.phenotype_drs`
      	where Weight_KG between 92.5 and 93.0
      	LIMIT 3"""
  		
	results = searchClient.runQuery(crdcquery)  # Send the query
	creditor.creditFromList('ISBGDCData')
	results += searchClient.runQuery(bdcquery)  
	creditor.creditFromList('BDCData')

	# Step 2 - DRS - set up DRS Clients
	
	# For later!
	# mr = MyMetaResolver()
	
	drsClients = {
		"crdc": crdcDRSClient('~/.keys/CRDCAPIKey.json', ''),
		"bdc": bdcDRSClient('~/.keys/BDCcredentials.json', '')
	}
	print('setting credentials ')
	creditor.creditFromList('dbGaPFence')
	
	# Step 3 - set up a class that runs samtools for us
	# providing the location for the results
	mysam = GCPLSsamtools('gs://isbcgc-216220-life-sciences/fasand/')
	
	# A log is helpful to keep track of the computes we've submitted
	pipelineLogger = FASPLogger("./pipelineLog.txt", os.path.basename(__file__))
	
	# repeat steps 2 and 3 for each row of the query
	for row in results:

		print("subject={}, drsID={}".format(row[0], row[1]))
		
		# Step 2 - Use DRS to get the URL
		# get the prefix
		prefix, drsid = row[1].split(":", 1)
		url = drsClients[prefix].getAccessURL(drsid, 'gs')
		drsClient = drsClients[prefix]
		creditor.creditClass(drsClient)
		objInfo = drsClient.getObject(drsid)
		fileSize = objInfo['size']
				
		# Step 3 - Run a pipeline on the file at the drs url
		outfile = "{}.txt".format(row[0])
		mysam.runWorkflow(url, outfile)
		creditor.creditClass(mysam)
		via = 'sh'
		pipeline_id = 'paste here'
		note = 'Two sources'
		time = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
		pipelineLogger.logRun(time, via, note,  pipeline_id, outfile, fileSize,
			searchClient, drsClient, mysam)
			
	pipelineLogger.close()
	creditor.creditFromList('FASPScript2_sdrf', closeImage=False)
    
if __name__ == "__main__":
    main(sys.argv[1:])
    


	
	

	
	









