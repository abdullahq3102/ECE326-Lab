# ECE326-Lab
Abdullah Qureshi
Justin Wang

# Instructions
install requirements with `pip install -r requirements.txt`
run frontend with `python app.py`
run backend with `python crawler.py`
Increase terminal line count to see full output from crawler.py if necessary
run unit tests via `python -m unittest test_crawler.py`


# Lab 4
Currently being hosted on http://44.220.154.207:8082/

## For deploying/running web server
make sure to configure your aws CLI to create the security group
run ec2 instance with `python deploy_ec2.py`
It will put the link to the frontend in the terminal
It also showed the ip address and instance id for the created instance

## For running benchmark
run benchmarking with `python deploy_benchmark_instance.py`
then type in link to frontend in the terminal to run the benchmarking tests on that web page
results will be put into results.txt file

## For terminating instances
For terminating instance by ip address
`python terminate_instances.py <instance-ip>`
For terminating instance by instance id
`python terminate_instances.py <instance-id>`
For terminating all running instances
`python terminate_instances.py all`

## Code Organization

### Files and Folders

- **`app.py`**: Frontend code
- **`crawler.py`**: Backend code for creating db
- **`test_crawler.py`**: Unit tests for backend
- **`deploy_ec2.py`**: script to deploy instance and run search engine in 1 click
- **`deploy_benchmark_instance.py`**: Script to benchmark instance
- **`terminate_instances.py`**: Script to terminate instances
- **`static/`**: Contains png and gif logo
- **`templates/`**: Contains HTML templates for frontend
- **`requirements.txt`**: necessary python dependencies
- **`crawler_data.db`**: actual database file
