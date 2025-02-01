from flask import Flask, request, jsonify
import threading
import os
import logging
import boto3
import json
import time

# Initialize Flask app and logging
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
aws_region = "us-east-1"

# Initialize AWS clients
sqs = boto3.client('sqs', region_name=aws_region)
ec2 = boto3.resource('ec2', region_name=aws_region)
s3 = boto3.client('s3', region_name=aws_region)

# SQS URLs and S3 bucket name
request_queue_url = "https://sqs.us-east-1.amazonaws.com/796973512232/1230040424-req-queue"
response_queue_url = "https://sqs.us-east-1.amazonaws.com/796973512232/1230040424-resp-queue"
input_bucket = "1230040424-in-bucket"

# Autoscaling parameters
max_instances = 19
min_instances = 0
scale_up_threshold = 1
scale_down_threshold = 1
security_group_id = "sg-0fca862ba2af11de5"  # Replace with actual security group
ami_id = "ami-06d63f4b95aca64e0"  # Replace with your AMI ID
key_name = 'Yuhsiang_Huang'  # Replace with your key pair name

cache={}


def autoscale():
    """
    Autoscaling logic that scales EC2 instances based on the number of messages in the SQS queue.
    """
    while True:
        try:
            # Get the number of messages in the queue
            response = sqs.get_queue_attributes(
                QueueUrl=request_queue_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            num_messages = int(response['Attributes']['ApproximateNumberOfMessages'])

            # Get the number of running app-tier instances
            instances = list(ec2.instances.filter(
                Filters=[
                    {'Name': 'instance-state-name', 'Values': ['running']},
                    {'Name': 'tag:Name', 'Values': ['app-tier-instance']}
                ]
            ))
            num_instances = len(instances)

            # Scale up aggressively
            if num_messages >= scale_up_threshold and num_instances < max_instances:
                ec2.create_instances(
                    ImageId=ami_id,
                    InstanceType='t2.micro',
                    MinCount=1,
                    MaxCount=1,
                    SecurityGroupIds=[security_group_id],
                    KeyName=key_name,
                    TagSpecifications=[
                        {
                            'ResourceType': 'instance',
                            'Tags': [{'Key': 'Name', 'Value': 'app-tier-instance'}]
                        }
                    ],
                )   

            # Scale down more than one instance if necessary
            elif num_messages < scale_down_threshold and num_instances > min_instances:
                instance_to_terminate = next(iter(instances))
                instance_to_terminate.terminate()
        except Exception as e:
            logging.error(f"Error in autoscaling: {e}")

        time.sleep(20)  

threading.Thread(target=autoscale, daemon=True).start()


@app.route('/', methods=['POST'])
def classify_image():
    
    if 'inputFile' not in request.files:
        return "Error: File not found", 400

    file = request.files['inputFile']
    if file.filename == '':
        return "Error: No selected file", 400

    filename = os.path.basename(file.filename)
    base_filename = os.path.splitext(filename)[0]
    logging.info(f"Received file: {filename}")

    try:
        s3.put_object(Bucket=input_bucket, Key=filename, Body=file.read())
        logging.info(f"Uploaded file to S3: {filename}")
    except Exception as e:
        logging.error(f"Error uploading to S3: {e}")
        return "Error: Failed to upload file", 500

    try:
        sqs.send_message(
            QueueUrl=request_queue_url,
            MessageBody=json.dumps({'image_name': base_filename})
        )
        logging.info(f"Sent message to request queue: {base_filename}")
    except Exception as e:
        logging.error(f"Error sending message to SQS: {e}")
        return "Error: Failed to send message", 500
    
    
    while True:
            if base_filename in cache:
                cached_data = cache[base_filename]
                logging.info(f"Found {base_filename} in cache. Deleting corresponding SQS message...")
                
                # Use the cached ReceiptHandle to delete the message from SQS
                receipt_handle = cached_data['ReceiptHandle']
                sqs.delete_message(
                    QueueUrl=response_queue_url,
                    ReceiptHandle=receipt_handle
                )
                logging.info(f"Deleted message from SQS for {base_filename}")

                del cache[base_filename]
                logging.info(f"Deleted {base_filename} from cache.")

                return f"{base_filename}: {cached_data['result']}"
            
            response = sqs.receive_message(
                QueueUrl=response_queue_url,
                MaxNumberOfMessages=10,  # Get one message at a time
                WaitTimeSeconds=1  # Use long polling to wait for new messages
            )

            # Check if a message is received
            if 'Messages' in response:
                for message in response['Messages']:
                    body = json.loads(message['Body'])
                    image_name = body['image_name']
                    result = body['result']
                    receipt_handle = message['ReceiptHandle']
                    # Cache both the result and the ReceiptHandle
                    cache[image_name] = {
                        'result': result,
                        'ReceiptHandle': receipt_handle
                    }
                    logging.info(f"Cached result for {image_name}")
                    # Check if the message contains the result for the current file
                    if image_name == base_filename:
                        
                        sqs.delete_message(
                            QueueUrl=response_queue_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )
                        logging.info(f"Deleted message from response queue: {body['image_name']}")
                        return f"{image_name}: {result}"
            else:
                logging.info(f"No messages available in the queue for {base_filename}. Waiting...")

              



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=80)