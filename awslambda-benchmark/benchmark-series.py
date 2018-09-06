import argparse 
import json 
import sys, os
import queue
import threading

import boto3
from botocore import UNSIGNED
from botocore.config import Config


parser = argparse.ArgumentParser(description='Run a benchmark')
parser.add_argument('mode', help='are we using the AWS endpoint or localhost?')
parser.add_argument('--parallelism', default=1, type=int, 
    help='how many threads to test on, run completes when last thread terminates')
parser.add_argument('--count', default=100, type=int, 
    help='how many threads to test on, run completes when last thread terminates')
parser.add_argument('--sleep', default=-1, type=float, 
    help='hog long the job should sleep for')
args = parser.parse_args()

if args.mode.lower() == "localhost": 
    print("LOCALHOST MODE")
    awslambda = boto3.client('lambda', 
        config=Config(signature_version=UNSIGNED),
        endpoint_url="http://localhost:80"
    )

elif args.mode.lower() == "ec2":
    
    print("Using a hard-coded ec2 instance")
    awslambda = boto3.client('lambda', 
        config=Config(signature_version=UNSIGNED),
        endpoint_url="http://cspot.lastpengu.in:80"
    )

elif args.mode.lower() == "aws":
    print("AWS MODE")
    with open('aws.json', 'r') as f:
        aws_creds = json.load(f)
    
    awslambda = boto3.client('lambda', 
        aws_access_key_id=aws_creds["aws_access_key_id"],
        aws_secret_access_key=aws_creds["aws_secret_access_key"],
        region_name='us-west-2',
    )
else:

    print("Invalid mode was specified.")
    sys.exit(1)


jobqueue = queue.Queue()
resultqueue = queue.Queue()

payload_obj = {
    "a": 10,
    "b": 11,
}
if args.sleep > 0:
    payload_obj["sleep"] = args.sleep
payload = bytes(json.dumps(payload_obj), "ascii")

def job(thread_id):
    global payload
    print("lambda invoke on thread: %d" % thread_id)
    response = awslambda.invoke(
        FunctionName="add",
        InvocationType="RequestResponse",
        Payload=payload
    )
    print("thread %d response: %s" % (thread_id, str(response)))
    return response["Payload"].read()

for i in range(args.count):
    jobqueue.put(job)

def run_test(jobqueue, resultqueue, thread_id):
    while True:
        job = jobqueue.get()
        resultqueue.put(job(thread_id))

for i in range(args.parallelism):
    print("spawning thread #%d" % i)
    t = threading.Thread(target=run_test, args = (jobqueue, resultqueue, i))
    t.daemon = True
    t.start()

for x in range(args.count):
    print("got result #%d: %s" % (x, resultqueue.get().decode('ascii')))

