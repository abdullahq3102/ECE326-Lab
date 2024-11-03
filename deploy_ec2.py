import boto3
import time
import paramiko
from scp import SCPClient

# Initialize AWS session
ec2 = boto3.resource('ec2', region_name='us-east-1')
client = boto3.client('ec2', region_name='us-east-1')

# Security Group Setup
def create_security_group():
    # Check if the security group already exists
    groupName = 'ece326-group5'
    try:
        response = client.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [groupName]}]
        )
        if response['SecurityGroups']:
            security_group_id = response['SecurityGroups'][0]['GroupId']
            print(f"Using existing Security Group: {security_group_id}")
            return security_group_id
    except client.exceptions.ClientError as e:
        print(f"Error checking for existing security group: {e}")
    
    # Create a new security group if it doesn't exist
    try:
        response = client.create_security_group(
            GroupName=groupName,
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
        print(f"Error creating security group: {e}")
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
        exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

        # Update package manager and install Python3
        sudo yum update -y
        sudo yum install -y python3 git

        # Install pip if it is not installed
        curl -O https://bootstrap.pypa.io/get-pip.py
        sudo python3 get-pip.py

        # Switch to the ec2-user environment
        cd /home/ec2-user
        sudo -u ec2-user -H sh -c '

        # Clone the repository
        git clone https://github.com/abdullahq3102/ECE326-Lab || echo "Repository already exists"

        # Change directory to the cloned repository
        cd ECE326-Lab

        # Install project dependencies
        pip3 install --user -r requirements.txt
        '
        ''',
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'ECE326_Lab2_Instance'}]}]
    )
    instance = instances[0]
    print("Launching EC2 instance...")
    instance.wait_until_running()
    instance.reload()
    print(f"EC2 instance launched. Public IP: {instance.public_ip_address}")
    return instance.public_ip_address, instance

# Upload oauthSecrets.json and restart app
import os
import time

def setup_instance(public_ip):
    key = paramiko.RSAKey.from_private_key_file("ECE326_lab.pem")  # Ensure correct path
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Retry SSH connection until successful
    connected = False
    while not connected:
        try:
            ssh_client.connect(hostname=public_ip, username="ec2-user", pkey=key)
            connected = True
        except Exception as e:
            print(f"SSH connection failed: {e}, retrying in 10 seconds...")
            time.sleep(10)

    # Wait for initial setup (e.g., git clone and pip install) to complete
    print("Waiting for instance setup to complete...")
    time.sleep(30)

    # Ensure the ECE326-Lab directory exists
    stdin, stdout, stderr = ssh_client.exec_command("mkdir -p /home/ec2-user/ECE326-Lab")
    print("Ensured that /home/ec2-user/ECE326-Lab exists.")
    print(stderr.read().decode())

    # Use SCP to transfer the oauthSecrets.json file
    with SCPClient(ssh_client.get_transport()) as scp:
        scp.put("oauthSecrets.json", "/home/ec2-user/ECE326-Lab/oauthSecrets.json")
    print("oauthSecrets.json uploaded to instance.")
    time.sleep(10)

    # Start app.py in the background and detach after a short wait
    commands = [
    "pkill -f app.py || echo 'app.py not running'",  # Kill any running instance of app.py
    "cd /home/ec2-user/ECE326-Lab && nohup python3 app.py > output.log 2>&1 &"  # Run app.py in background from the correct directory
    ]
    for command in commands:
        stdin, stdout, stderr = ssh_client.exec_command(command, get_pty=False, timeout=5)
        print(f"Executing: {command}")
        # print(stdout.read().decode())
        # print(stderr.read().decode())

    # Wait briefly to ensure app.py starts, then close the SSH connection
    time.sleep(5)
    ssh_client.close()
    print("SSH session closed after launching app.py.")



# Main function
def main():
    security_group_id = create_security_group()
    if security_group_id:
        public_ip, instance = launch_instance(security_group_id)

        # Wait a bit to allow instance setup to complete
        time.sleep(5)

        # Upload oauthSecrets.json and restart app.py
        setup_instance(public_ip)
        
        print(f"Application deployed and accessible at http://{public_ip}:8082")
        print(f'To connect to the instance via SSH, use the following command:\nssh -i "ECE326_lab.pem" ec2-user@{public_ip}')

if __name__ == "__main__":
    main()
