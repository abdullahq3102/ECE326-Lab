import boto3
import time

# Initialize AWS session
ec2 = boto3.resource('ec2', region_name='us-east-1')
client = boto3.client('ec2', region_name='us-east-1')

# Security Group Setup
def create_security_group():
    try:
        response = client.create_security_group(
            GroupName='ece326-group25',
            Description='Security group for ECE326 Lab deployment'
        )
        security_group_id = response['GroupId']

        # Configure Security Group Ingress Rules
        client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {'IpProtocol': 'icmp', 'FromPort': -1, 'ToPort': -1, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 8082, 'ToPort': 8082, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ]
        )
        print(f"Security Group {security_group_id} created and configured.")
        return security_group_id
    except client.exceptions.ClientError as e:
        print(f"Error: {e}")
        return None

# Launch EC2 Instance
def launch_instance(security_group_id):
    instances = ec2.create_instances(
        ImageId='ami-06b21ccaeff8cd686',  # Amazon Linux 2 AMI in us-east-1
        InstanceType='t2.micro',
        KeyName='ECE326_lab',  # Replace with the name of your key pair (without .pem)
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[security_group_id],
        UserData='''#!/bin/bash
        # Update package manager and install Python3
        sudo yum update -y
        sudo yum install -y python3 git

        # Install pip if it is not installed
        curl -O https://bootstrap.pypa.io/get-pip.py
        sudo python3 get-pip.py

        # Clone the repository
        git clone https://github.com/abdullahq3102/ECE326-Lab

        # Change directory to the cloned repository
        cd ECE326-Lab

        # Install project dependencies
        pip3 install -r requirements.txt

        # Run the application in the background
        nohup python3 app.py > output.log 2>&1 &
        ''',
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'ECE326_Lab2_Instance'}]}]
    )
    instance = instances[0]
    print("Launching EC2 instance...")
    instance.wait_until_running()
    instance.reload()
    print(f"EC2 instance launched. Public IP: {instance.public_ip_address}")
    return instance.public_ip_address

# Main function
def main():
    security_group_id = create_security_group()
    if security_group_id:
        public_ip = launch_instance(security_group_id)
        print(f"Application deployed and accessible at http://{public_ip}:8082")

if __name__ == "__main__":
    main()
