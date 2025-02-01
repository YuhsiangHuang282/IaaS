Elastic Face Recognition Application
This project implements an elastic face recognition application deployed on AWS Infrastructure as a Service (IaaS), utilizing multiple AWS services including EC2, S3, and SQS. The application is designed to dynamically scale and efficiently process face recognition tasks.

Project Overview
The application is structured into three main tiers:
  Web Tier: Manages user requests and responses.
  App Tier: Processes the face recognition using a machine learning model.
  Data Tier: Handles persistent storage of images and recognition results.

Features:
  Scalable face recognition processing.
  Dynamic resource allocation based on demand.
  Secure and compliant data handling.
  High availability and disaster recovery capabilities.

Prerequisites
  AWS Account
  AWS CLI configured on your local machine
  Python 3.x
  Boto3 library (AWS SDK for Python)
  Configure AWS Services
    S3 Buckets: Create two S3 buckets, one for input and one for output. Adjust the bucket names in the configuration files accordingly.
    SQS Queues: Set up two SQS queues, one for requests and one for responses. Ensure the queue URLs are updated in the scripts.
    EC2 Instances: Launch an EC2 instance using an AMI that includes all necessary dependencies for the face recognition model.



Contact
For support or queries, reach out via email at vincentohstudy@gmail.com.
