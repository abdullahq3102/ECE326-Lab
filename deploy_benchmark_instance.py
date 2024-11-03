import boto3
import time
import paramiko

# Initialize AWS session
ec2 = boto3.resource('ec2', region_name='us-east-1')
client = boto3.client('ec2', region_name='us-east-1')

def create_security_group():
    try:
        response = client.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': ['benchmark-sg']}]
        )
        if response['SecurityGroups']:
            security_group_id = response['SecurityGroups'][0]['GroupId']
            print(f"Using existing Security Group: {security_group_id}")
            return security_group_id
    except client.exceptions.ClientError as e:
        print(f"Error checking for existing security group: {e}")

    try:
        response = client.create_security_group(
            GroupName='benchmark-sg',
            Description='Security group for benchmarking instance'
        )
        security_group_id = response['GroupId']

        # Configure Security Group Ingress Rules
        client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ]
        )
        print(f"Security Group {security_group_id} created and configured.")
        return security_group_id
    except client.exceptions.ClientError as e:
        print(f"Error creating security group: {e}")
        return None

def launch_benchmark_instance(security_group_id):
    instances = ec2.create_instances(
        ImageId='ami-06b21ccaeff8cd686',  # Amazon Linux 2 AMI
        InstanceType='t2.micro',
        KeyName='ECE326_lab',  # Ensure this is your existing key pair name
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[security_group_id],
        UserData='''#!/bin/bash
        # Install Apache Bench and htop
        sudo yum update -y
        sudo yum install -y httpd-tools htop

        # Optional: Install sysstat for advanced monitoring
        sudo yum install -y sysstat
        sudo systemctl enable sysstat
        sudo systemctl start sysstat
        ''',
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'Benchmark_Instance'}]}]
    )
    instance = instances[0]
    print("Launching EC2 instance for benchmarking...")
    instance.wait_until_running()
    instance.reload()
    print(f"Benchmark instance launched. Public IP: {instance.public_ip_address}")
    return instance.public_ip_address, instance

def run_benchmark(ssh_client, target_url):
    # Run Apache Bench and monitoring tools on the target URL
    benchmark_command = f"ab -n 100 -c 10 {target_url} > benchmark_results.txt"
    cpu_command = "sar -u 1 5 > cpu_usage.txt"  # Run sysstat for CPU utilization over 5 seconds

    # Execute the benchmark and CPU usage commands
    print(f"Running benchmark on {target_url}...")
    ssh_client.exec_command(benchmark_command)
    ssh_client.exec_command(cpu_command)

    # Retrieve benchmark results
    stdin, stdout, stderr = ssh_client.exec_command("cat benchmark_results.txt")
    benchmark_results = stdout.read().decode()

    # Retrieve CPU usage log
    stdin, stdout, stderr = ssh_client.exec_command("cat cpu_usage.txt")
    cpu_usage = stdout.read().decode()

    # Write results to file
    with open("results.txt", "a") as f:
        f.write(f"\nBenchmark results for {target_url}:\n")
        f.write(benchmark_results)
        f.write("\nCPU usage during benchmark:\n")
        f.write(cpu_usage)
        f.write("\n" + "="*40 + "\n")

    print(f"Results for {target_url} appended to results.txt.")

# Main function
def main():
    security_group_id = create_security_group()
    if not security_group_id:
        print("Could not create or find security group. Exiting.")
        return

    public_ip, instance = launch_benchmark_instance(security_group_id)

    # Wait for instance setup to complete
    print("Waiting for instance to initialize...")
    time.sleep(60)

    # Connect to the instance
    key = paramiko.RSAKey.from_private_key_file("ECE326_lab.pem")  # Ensure correct path
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

    # Run benchmarks in a loop until the user decides to stop
    while True:
        target_url = input("Enter the target URL to benchmark (or type 'exit' to quit): ")
        if target_url.lower() == "exit":
            print("Exiting benchmarking session.")
            break
        run_benchmark(ssh_client, target_url)

    # Close SSH connection after benchmarking
    ssh_client.close()
    print("SSH session closed. Benchmarking complete.")

if __name__ == "__main__":
    main()
