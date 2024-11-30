import boto3
import sys

def get_instance_id_by_ip(ec2_client, public_ip):
    """Fetch the instance ID using its public IP address."""
    try:
        response = ec2_client.describe_instances(
            Filters=[{'Name': 'ip-address', 'Values': [public_ip]}]
        )
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                return instance['InstanceId']
    except Exception as e:
        print(f"Error while fetching instance ID by IP: {e}")
    return None

def terminate_instances(identifier=None):
    # Create an EC2 resource and client
    ec2 = boto3.resource('ec2')
    ec2_client = boto3.client('ec2')

    try:
        if identifier and identifier != "all":
            if identifier.startswith("i-"):
                # Terminate a specific instance by instance ID
                instance_id = identifier
            else:
                # Treat the identifier as an IP address
                print(f"Fetching instance ID for public IP: {identifier}")
                instance_id = get_instance_id_by_ip(ec2_client, identifier)
                if not instance_id:
                    print(f"No instance found with public IP: {identifier}")
                    return
            
            print(f"Attempting to terminate instance: {instance_id}")
            response = ec2_client.terminate_instances(InstanceIds=[instance_id])
            print("Termination initiated for the instance:")
            for instance in response['TerminatingInstances']:
                print(f"Instance ID: {instance['InstanceId']} - Current State: {instance['CurrentState']['Name']}")

        elif identifier == "all":
            # Retrieve all running instances
            instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
            instance_ids = [instance.id for instance in instances]

            if not instance_ids:
                print("No running instances found to terminate.")
                return

            print(f"Found the following running instances to terminate: {instance_ids}")

            # Terminate instances
            response = ec2_client.terminate_instances(InstanceIds=instance_ids)
            print("Termination initiated for the following instances:")
            for instance in response['TerminatingInstances']:
                print(f"Instance ID: {instance['InstanceId']} - Current State: {instance['CurrentState']['Name']}")
        else:
            print("Invalid argument. Provide a valid instance ID, public IP, or 'all'.")
    except Exception as e:
        print(f"Error while terminating instances: {e}")

if __name__ == "__main__":
    # Get the command-line argument (instance ID, public IP, or "all")
    if len(sys.argv) < 2:
        print("Usage: python terminate_instances.py <instance_id | public_ip | all>")
    else:
        identifier = sys.argv[1]
        terminate_instances(identifier)
