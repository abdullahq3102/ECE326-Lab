# ECE326-Lab
Abdullah Qureshi
Justin Wang

# Instructions
install requirements with `pip install -r requirements.txt`
run frontend with `python app.py`
run backend with `python crawler.py`
Increase terminal line count to see full output from crawler.py if necessary
run unit tests via `python -m unittest test_crawler.py`


# Lab 2
Currently being hosted on http://54.160.252.208:8082/
## For running web server
run ec2 instance with `python deploy_ec2.py`
It will put the link to the frontend in the terminal

## For running benchmark
run benchmarking with `python deploy_benchmark_instance.py`
then type in link to frontend in the terminal to run the benchmarking tests on that web page
results will be put into results.txt file
