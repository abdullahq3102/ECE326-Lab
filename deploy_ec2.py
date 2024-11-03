import boto3
import time
import paramiko
from scp import SCPClient


ec2 = boto3.resource('ec2', region_name='us-east-1')
client = boto3.client('ec2', region_name='us-east-1')


def create_security_group():
    
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
    
    
    try:
        response = client.create_security_group(
            GroupName=groupName,
            Description='Security group for ECE326 Lab deployment'
        )
        security_group_id = response['GroupId']

        
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



def launch_instance(security_group_id):
    instances = ec2.create_instances(
        ImageId='ami-06b21ccaeff8cd686',  
        InstanceType='t2.micro',
        KeyName='ECE326_lab',  
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[security_group_id],
        UserData='''#!/bin/bash
        exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

        sudo yum update -y
        sudo yum install -y python3 git

        curl -O https://bootstrap.pypa.io/get-pip.py
        sudo python3 get-pip.py

        cd /home/ec2-user
        sudo -u ec2-user -H sh -c '

        git clone https://github.com/abdullahq3102/ECE326-Lab || echo "Repository already exists"

        cd ECE326-Lab

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


import os
import time

def setup_instance(public_ip):
    key = paramiko.RSAKey.from_private_key_file("ECE326_lab.pem")  
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    
    connected = False
    while not connected:
        try:
            ssh_client.connect(hostname=public_ip, username="ec2-user", pkey=key)
            connected = True
        except Exception as e:
            print(f"SSH connection failed: {e}, retrying in 10 seconds...")
            time.sleep(10)

    
    print("Waiting for instance setup to complete...")
    time.sleep(30)

    
    stdin, stdout, stderr = ssh_client.exec_command("mkdir -p /home/ec2-user/ECE326-Lab")
    print("Ensured that /home/ec2-user/ECE326-Lab exists.")
    print(stderr.read().decode())

    
    with SCPClient(ssh_client.get_transport()) as scp:
        scp.put("oauthSecrets.json", "/home/ec2-user/ECE326-Lab/oauthSecrets.json")
    print("oauthSecrets.json uploaded to instance.")
    time.sleep(10)

    
    commands = [
    "pkill -f app.py || echo 'app.py not running'",  
    "cd /home/ec2-user/ECE326-Lab && nohup python3 app.py > output.log 2>&1 &"  
    ]
    for command in commands:
        stdin, stdout, stderr = ssh_client.exec_command(command, get_pty=False, timeout=5)
        print(f"Executing: {command}")
        
        

    
    time.sleep(5)
    ssh_client.close()
    print("SSH session closed after launching app.py.")




def main():
    security_group_id = create_security_group()
    if security_group_id:
        public_ip, instance = launch_instance(security_group_id)

        
        time.sleep(5)

        
        setup_instance(public_ip)
        
        print(f"Application deployed and accessible at http://{public_ip}:8082")
        print(f'To connect to the instance via SSH, use the following command:\nssh -i "ECE326_lab.pem" ec2-user@{public_ip}')

if __name__ == "__main__":
    main()
