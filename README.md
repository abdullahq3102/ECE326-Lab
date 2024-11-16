# ECE326-Lab
Abdullah Qureshi
Justin Wang

# Instructions
install requirements with `pip install -r requirements.txt`
run frontend with `python app.py`
run backend with `python crawler.py`
Increase terminal line count to see full output from crawler.py if necessary
run unit tests via `python -m unittest test_crawler.py`


# Lab 3
Currently being hosted on http://3.92.1.195:8082/
## For running web server
make sure to configure your aws CLI to create the security group
run ec2 instance with `python deploy_ec2.py`
It will put the link to the frontend in the terminal

## For running benchmark
run benchmarking with `python deploy_benchmark_instance.py`
then type in link to frontend in the terminal to run the benchmarking tests on that web page
results will be put into results.txt file


# D3 Benchmark Comparison
The benchmark results for lab 3 were slightly worse than that of lab2. This makes sense because it has to make several database calls on new search results, This can be seen in the results per second decreasing from 440 to 418. However, the throughput and latency scores were improved, throughput going from 346 to 360 and latency going form 28.8 to 27.7. However, this seems to be marginal and we will just attribute to random causes like network and system load.