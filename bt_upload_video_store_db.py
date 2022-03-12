#https://github.com/Azure-Samples/media-services-v3-python
# for key access description:  https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python?tabs=environment-variable-windows
#samples:  https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-blob/samples

from datetime import datetime, timedelta
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient, generate_blob_sas, BlobSasPermissions, BlobServiceClient
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.mgmt.media import AzureMediaServices

from azure.mgmt.media.models import (
  Asset,
  Transform,
  TransformOutput,
  BuiltInStandardEncoderPreset,
  Job,
  JobInputAsset,
  JobOutputAsset)
import os
import decouple
import pyodbc

#Timer for checking job progress
import time

#This is only necessary for the random number generation (uniqueness)
import random

#Get environmant variables
load_dotenv()

# Get the default Azure credential from the environment variables AZURE_CLIENT_ID and AZURE_CLIENT_SECRET and AZURE_TENTANT_ID
default_credential = DefaultAzureCredential()

# The file you want to upload.  For this example, put the file in the same folder as this script. 
# The file ignite.mp4 has been provided for you. 
#source_file = "SampleVideoWthRobot.mp4"

server = 'buckeyewildcats.database.windows.net'
database = 'batterytracker'
username = decouple.config('UserID',default='')
password = decouple.config('password',default='') 

cnxn = pyodbc.connect('DRIVER={SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+ password)
cursor = cnxn.cursor()
            # Insert Dataframe into SQL Server:
query = """SELECT ID from bt_plan where starttime= (SELECT MAX(starttime) FROM bt_plan)""" 
cursor.execute(query)
row = cursor.fetchone()
UID = (row[0])

#source_file = 'EA117892-A68E-4265-AE1A-48811BECA4C2.mp4'
source_file = UID + '.mp4'


# Generate a random number that will be added to the naming of things so that you don't have to keep doing this during testing.
uniqueness = random.randint(0,9999)

# Set the attributes of the input Asset using the random number
in_asset_name = 'inputassetName' + str(uniqueness)
in_alternate_id = 'inputALTid' + str(uniqueness)
in_description = 'inputdescription' + str(uniqueness)

# Create an Asset object
# From the SDK
# Asset(*, alternate_id: str = None, description: str = None, container: str = None, storage_account_name: str = None, **kwargs) -> None
# The asset_id will be used for the container parameter for the storage SDK after the asset is created by the AMS client.
input_asset = Asset(alternate_id=in_alternate_id,description=in_description)

# Set the attributes of the output Asset using the random number
out_asset_name = 'outputassetName' + str(uniqueness)
out_alternate_id = 'outputALTid' + str(uniqueness)
out_description = 'outputdescription' + str(uniqueness)
# From the SDK
# Asset(*, alternate_id: str = None, description: str = None, container: str = None, storage_account_name: str = None, **kwargs) -> None
output_asset = Asset(alternate_id=out_alternate_id,description=out_description)
print('the output asset is:')
print(output_asset)

# The AMS Client
print("Creating AMS client")
# From SDK
# AzureMediaServices(credentials, subscription_id, base_url=None)
client = AzureMediaServices(default_credential, os.getenv('SUBSCRIPTIONID'))

# Create an input Asset
print("Creating input asset " + in_asset_name)
# From SDK
# create_or_update(resource_group_name, account_name, asset_name, parameters, custom_headers=None, raw=False, **operation_config)
inputAsset = client.assets.create_or_update( os.getenv("RESOURCEGROUP"), os.getenv("ACCOUNTNAME"), in_asset_name, input_asset)

# An AMS asset is a container with a specific id that has "asset-" prepended to the GUID.
# So, you need to create the asset id to identify it as the container
# where Storage is to upload the video (as a block blob)
in_container = 'asset-' + inputAsset.asset_id
print('input container')
print(in_container)

# create an output Asset
print("Creating output asset " + out_asset_name)
# From SDK
# create_or_update(resource_group_name, account_name, asset_name, parameters, custom_headers=None, raw=False, **operation_config)
outputAsset = client.assets.create_or_update(os.getenv("RESOURCEGROUP"), os.getenv("ACCOUNTNAME"), out_asset_name, output_asset)
print('output asset')
print(outputAsset)
out_continer  = 'asset-' + outputAsset.asset_id
print('output continer')
print(out_continer)

#print(out_asset_name)
#print(outputAsset)
#print(output_asset)

### Use the Storage SDK to upload the video ###
print("Uploading the file " + source_file)

blob_service_client = BlobServiceClient.from_connection_string(os.getenv('STORAGEACCOUNTCONNECTION'))


# From SDK
# get_blob_client(container, blob, snapshot=None)
blob_client = blob_service_client.get_blob_client(in_container,source_file)
##########################################################
#print(in_container) #this prints the input container
###########################################################

#working_dir = os.getcwd()
working_dir = "C:\\scripts\\OpenCV_AI_Competetion\\web_connect_to_video"

print("Current working directory:" + working_dir)
upload_file_path = os.path.join(working_dir, source_file)

# WARNING: Depending on where you are launching the sample from, the path here could be off, and not include the BasicEncoding folder. 
# Adjust the path as needed depending on how you are launching this python sample file. 

# Upload the video to storage as a block blob
with open(upload_file_path, "rb") as data:
  # From SDK
  # upload_blob(data, blob_type=<BlobType.BlockBlob: 'BlockBlob'>, length=None, metadata=None, **kwargs)

    blob_client.upload_blob(data)
print('uploading file')
### Create a Transform ###
#transform_name='MyTrans' + str(uniqueness)
transform_name='StandardTransform_BatteryTracker'
# From SDK
# TransformOutput(*, preset, on_error=None, relative_priority=None, **kwargs) -> None
#transform_output = TransformOutput(preset=BuiltInStandardEncoderPreset(preset_name="AdaptiveStreaming"))
transform_output = TransformOutput(preset=BuiltInStandardEncoderPreset(preset_name="ContentAwareEncoding"))

#print(transform_output)

transform = Transform()
transform.outputs = [transform_output]

print("Creating transform " + transform_name)
# From SDK
# Create_or_update(resource_group_name, account_name, transform_name, outputs, description=None, custom_headers=None, raw=False, **operation_config)
transform = client.transforms.create_or_update(
  resource_group_name=os.getenv("RESOURCEGROUP"),
  account_name=os.getenv("ACCOUNTNAME"),
  transform_name=transform_name,
  parameters = transform)

### Create a Job ###
job_name = 'MyJob'+ str(uniqueness)
print("Creating job " + job_name)
files = (source_file)

# From SDK
# JobInputAsset(*, asset_name: str, label: str = None, files=None, **kwargs) -> None
input = JobInputAsset(asset_name=in_asset_name)
# From SDK
# JobOutputAsset(*, asset_name: str, **kwargs) -> None
outputs = JobOutputAsset(asset_name=out_asset_name)

#print(out_asset_name)
#print(outputs)

# From SDK
# Job(*, input, outputs, description: str = None, priority=None, correlation_data=None, **kwargs) -> None
theJob = Job(input=input,outputs=[outputs])
# From SDK
# Create(resource_group_name, account_name, transform_name, job_name, parameters, custom_headers=None, raw=False, **operation_config)
job: Job = client.jobs.create(os.getenv("RESOURCEGROUP"),os.getenv('ACCOUNTNAME'),transform_name,job_name,parameters=theJob)

### Check the progress of the job ### 
# From SDK
# get(resource_group_name, account_name, transform_name, job_name, custom_headers=None, raw=False, **operation_config)
job_state = client.jobs.get(os.getenv("RESOURCEGROUP"),os.getenv('ACCOUNTNAME'),transform_name,job_name)
# First check
print("First job check")
print(job_state.state)

# Check the state of the job every 10 seconds. Adjust time_in_seconds = <how often you want to check for job state>
def countdown(t):
    while t: 
        mins, secs = divmod(t, 60) 
        timer = '{:02d}:{:02d}'.format(mins, secs) 
        print(timer, end="\r") 
        time.sleep(1) 
        t -= 1
    job_current = client.jobs.get(os.getenv("RESOURCEGROUP"),os.getenv('ACCOUNTNAME'),transform_name,job_name)
    #print(job_current)
    if(job_current.state == "Finished"):
      #print(job_current.state)
      # TODO: Download the output file using blob storage SDK
      return
    if(job_current.state == "Error"):
      print(job_current.state)
      # TODO: Provide Error details from Job through API
      return
    else:
      print(job_current.state)
      countdown(int(time_in_seconds))

time_in_seconds = 10
countdown(int(time_in_seconds))

########################################################
#Get the name of the blobs from the job
#Azure adds a suffix to the name so we need to get the 
#exact filename from the asset
########################################################
#container_client = blob_service_client.get_container_client("asset-c78e2f02-6671-4a9a-974b-92ec3b5b5dae")
container_client = blob_service_client.get_container_client(out_continer)

blob_list = container_client.list_blobs()

for blob in blob_list:
    print(blob.name)
    suffix = ".mp4"
    if blob.name.endswith(".mp4"):
        output_video_name = blob.name 
print(output_video_name)

###############################################

#account_name = 'batterytrackerstorage'
account_name = os.getenv("STORAGEACCOUNTNAME")
account_key = os.getenv("STORAGEACCOUNTKEY")
container_name = out_continer

#blob_name = 'output_Trim.mp4'  #how to create the .mp4 from the blob in Azure is next
#blob_name = 'SampleVideoWthRobot_300x300_AACAudio_247.mp4'

blob_name = output_video_name  #use the name created from the job in the blob
def get_blob_sas(account_name,account_key, container_name, blob_name):
    sas_blob = generate_blob_sas(account_name=account_name, 
                                container_name=container_name,
                                blob_name=blob_name,
                                account_key=account_key,
                                permission=BlobSasPermissions(read=True),
                                expiry=datetime.utcnow() + timedelta(hours=8760))
    return sas_blob

blob = get_blob_sas(account_name,account_key, container_name, blob_name)
print(blob)
URL = ''
#url = 'https://'+account_name+'.blob.core.windows.net/'+container_name+'/'+blob_name+'?'+blob
URL = 'https://'+account_name+'.blob.core.windows.net/'+container_name+'/'+blob_name+'?'+blob


HTML = """
<!DOCTYPE html>
<html>
<body>
<video width="300" height="300" controls>
<source src="%s">
</video>
</body>
</html>
""" %(URL)
print(URL)
print(UID)
print(HTML)

video_query = """INSERT INTO [dbo].[bt_video]([UID],[URL],[HTML])VALUES('%s','%s','%s')""" %(UID,URL,HTML)
print(video_query)
cursor.execute(video_query)
cnxn.commit()
cursor.close()

