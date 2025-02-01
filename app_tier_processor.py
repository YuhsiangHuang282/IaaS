import boto3
import json
import time
import subprocess
import logging
import os

# Initialize AWS clients
sqs = boto3.client('sqs', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')

# SQS Queue URLs
request_queue_url = "https://sqs.us-east-1.amazonaws.com/796973512232/1230040424-req-queue"
response_queue_url = "https://sqs.us-east-1.amazonaws.com/796973512232/1230040424-resp-queue"

# S3 Buckets
input_bucket = '1230040424-in-bucket'
output_bucket = '1230040424-out-bucket'

# Logging configuration
logging.basicConfig(level=logging.DEBUG)

def image_process(image_path):
    """
    Process the image using the face recognition model.
    The subprocess runs the external face recognition script and captures the output.
    """
    result = subprocess.run(['python3', "face_recognition.py", image_path], capture_output=True, text=True)
    return result.stdout.strip()

def download_image_from_s3(image_key):
    """
    Download an image from the input S3 bucket and save it locally.
    """
    file_obj = s3.get_object(Bucket=input_bucket, Key=image_key)
    file_content = file_obj['Body'].read()
    
    with open(image_key, 'wb') as f:
        f.write(file_content)
    
    logging.debug(f"Downloaded {image_key} from S3 and saved locally.")
    return image_key

def upload_recognition_result_to_s3(image_name, recognition_result):
    """
    Upload the recognition result to the output S3 bucket.
    """
    output_key = image_name
    s3.put_object(Bucket=output_bucket, Key=output_key, Body=recognition_result)
    logging.debug(f"Uploaded recognition result for {image_name} to S3.")

def send_message_to_response_queue(image_name, recognition_result):
    """
    Send the classification result to the response SQS queue.
    """
    
    sqs.send_message(
        QueueUrl=response_queue_url,
        MessageBody=json.dumps({'image_name': image_name, 'result': recognition_result})
    )
    logging.debug(f"Sent result for {image_name} to response queue.")

def process_messages_from_request_queue():
    """
    Continuously poll the request queue, process images, and send recognition results.
    """

    while True:
        response = sqs.receive_message(
            QueueUrl=request_queue_url,
            AttributeNames=['All'],
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20
        )

        if "Messages" in response:
            for message in response["Messages"]:
                receipt_handle = message['ReceiptHandle']
                body = json.loads(message['Body'])
                image_name=body["image_name"]
                image_key = f"{image_name}.jpg"

                # Download the image from S3 and process it
                download_image_from_s3(image_key)
                recognition_result = image_process(image_key)

                # Upload the recognition result to the output bucket and send the result to the response queue
                upload_recognition_result_to_s3(image_name, recognition_result)
                send_message_to_response_queue(image_name, recognition_result)

                #Clean up local image file
                os.remove(image_key)
                logging.debug(f"Deleted local file: {image_key}")

                # Delete the message from the request queue
                sqs.delete_message(QueueUrl=request_queue_url, ReceiptHandle=receipt_handle)
                logging.debug(f"Deleted message from request queue: {receipt_handle}")
        
        time.sleep(1)


process_messages_from_request_queue()