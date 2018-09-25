import io 
import zipfile 
import os 
import json 
import threading
import multiprocessing 
import time 
from http.server import BaseHTTPRequestHandler, HTTPServer

import boto3
import botocore
from botocore import UNSIGNED
from botocore.config import Config

# create a connection to the lambda server
def new_awslambda_conn():
    return boto3.client('lambda', 
        config=Config(signature_version=UNSIGNED),
        endpoint_url="http://localhost:8080"
    )
awslambda = new_awslambda_conn()

def create_or_update_lambda(awslambda, funcname, srcdir, handlername):
    split = handlername.split(".")
    archivename = split[0]
    
    file_like_object = io.BytesIO()
    zipfile_ob = zipfile.ZipFile(file_like_object, "a", zipfile.ZIP_DEFLATED, False)

    srcdir = os.path.abspath(srcdir)
    for root, dirs, files in os.walk(srcdir):
        for file in files:
            fpath = os.path.join(root, file)
            base = os.path.commonprefix([srcdir, fpath])
            archivepath = os.path.relpath(fpath, base)
            print("\tadding %s -> %s" % (fpath,archivepath))
            zipfile_ob.write(fpath, archivepath)

    zipfile_ob.close()

    file_like_object.seek(0)
    try:
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
    except botocore.exceptions.ClientError as e:
        print("failed to create lambda, it probably already exists")
        file_like_object.seek(0)
        awslambda.update_function_code(
            FunctionName = funcname, 
            ZipFile = file_like_object.read()
        )
        print("updated lambda instead")
    
    file_like_object.close()

class CallbackServer(BaseHTTPRequestHandler):
    completed = None

    def __init__(self, completed, *args):
        self.completed = completed
        BaseHTTPRequestHandler.__init__(self, *args)

    def do_GET(s):
        print("""Respond to a GET request.""")
        s.send_response(200)
        s.send_header("Content-type", "text/plain")
        s.end_headers()
        s.wfile.write(bytes(s.path, "ascii"))
        s.wfile.write(bytes("\nOK\n", "ascii"))

        id = s.path.split("=")[1]
        print("\tGET FOR ID: %s" % id)
        id_n = int(id)
        s.completed[id_n] = 1

    def do_POST(self):
        print( "incomming http: ", self.path )
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        post_data = self.rfile.read(content_length) # <--- Gets the data itself
        self.send_response(200)
        client.close()

def thread_invoke_lambda(thread_id, ids, requests_successful):
    time.sleep(1)

    print("invoking function... thread: %d" % thread_id)

    for id in ids:
        response = new_awslambda_conn().invoke(
            FunctionName="Test",
            InvocationType="RequestResponse",
            Payload=bytes(json.dumps({
                "url": "http://cspot.lastpengu.in:1234/?id=%s" % (str(id),)
            }), "ascii")
        )
        res = response["Payload"].read().decode("ascii")
        print("RAW RESULT FOR THREAD %d: %s" % (thread_id, res))
        result = json.loads(res)
        print("INVOKE RESULT FOR THREAD %d: %s" % (thread_id, str(result)))

        if result["status"] == "OK":
            print("thread %d: SUCCESS ON %d" % (thread_id, id)) 
            requests_successful[id] = True
        else:
            print("thread %d: ERROR ON %d"  % (thread_id, id))

def thread_start_server(completed):
    print("starting the callback server")
    def constructor(*args):
        cbh = CallbackServer(completed, *args)
        cbh.completed = completed 
        return cbh 
    cbs = HTTPServer(('0.0.0.0', 1234), constructor)
    cbs.completed = completed
    print("serving...")
    cbs.serve_forever()


print("creating the lambda for this test")
create_or_update_lambda(awslambda, "Test", "./lambda/", "main.test")


print("spawning off test executor and callback server threads")
all_ids = []
invoke_threads = []
thread_count = 10
size = 100

completed = multiprocessing.Array('i', [0 for val in range(size * thread_count)])
requests_successful = [False] * (size * thread_count)

for i in range(0, thread_count):
    ids = list(range(i * size, (i + 1) * size))
    all_ids += ids 
    invoke_threads.append(
        threading.Thread(target=thread_invoke_lambda, args=(i, ids, requests_successful))
    )

thread_webserver = multiprocessing.Process(target=thread_start_server, args=(completed,))
thread_webserver.daemon = True
thread_webserver.start()
for thread in invoke_threads:
    thread.start()

print("Main thread joining on child threads")
for thread in invoke_threads:
    thread.join()

print("Checking all results... %s" % (str(all_ids)))
for id in all_ids:
    if requests_successful[id] != True:
        print("INVOKE #%d FAILED TO GET RESULT" % id)
    if completed[id] == 0:
        print("INVOKE #%d FAILED TO HTTP GET (probably did not run)" % id)

# print(requests_successful)
# print(completed)

print("Done.")


