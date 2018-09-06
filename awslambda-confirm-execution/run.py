import io 
import zipfile 
import os 
import json 

import boto3
from botocore import UNSIGNED
from botocore.config import Config

awslambda = boto3.client('lambda', 
    config=Config(signature_version=UNSIGNED),
    endpoint_url="http://localhost:80"
)

def create_lambda(awslambda, funcname, srcdir, handlername):
    split = handlername.split(".")
    archivename = split[0]
    
    file_like_object = io.BytesIO()
    zipfile_ob = zipfile.ZipFile(file_like_object, "a", zipfile.ZIP_DEFLATED, False)

    for root, dirs, files in os.walk(srcdir):
        for file in files:
            print("\tadding %s" % (os.path.join(root,file),))
            zipfile_ob.write(os.path.join(root, file))

    zipfile_ob.close()

    file_like_object.seek(0)
    awslambda.create_function(
        FunctionName = funcname, 
        Code = { 
            "ZipFile": file_like_object.read()
        },
        Handler =  handlername,
        Role =  handlername, 
        Runtime = "python3.6",
        Description = "A lambda for %s" % handlername,
        MemorySize = 256, # my implementation does not respect this property
        Timeout = 30, # my implementatation does not respect this property
    )

    file_like_object.close()

create_lambda(awslambda, "Test", "./lambda/", "main.test")

print("invoking function...")
response = awslambda.invoke(
    FunctionName="Test",
    InvocationType="RequestResponse",
    Payload=bytes(json.dumps({
        "url": "http://www.google.com/"
    }), "ascii")
)

print("RESULT: " + str(response["Payload"].read()))