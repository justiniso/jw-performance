# Performance Testing Demo

The purpose of this app is to demonstrate in a highly simplified setup how you might gather and analyze key performance
metrics of JWPlayer's transcoders. An overview of how it works:

- Users upload images of any file format to /upload
- Those images are saved to /tmp and a job is added to the priority queue to transcode that image to .png
- Background workers receive those jobs and upon completion, report the metrics to redis
- The performance script will then retrieve the metrics from redis and produce a human-friendly summary

The idea is that during the lifetime of an asset, some portion of the job's time is spent being uploaded, in queue,
and processing. The metrics reported by the transcoder will allow us to track how much time is spent in each of those
stages.

## Output

This is a sample output across 8 workers. There were 4 users uploading various assets:

- user 1: 100 assets
- user 2: 750 assets
- user 3: 50 assets
- user 4: 10 assets

```
    TOTAL SECONDS (total time elapsed)
    100.218034


    TOTAL ASSETS (total number of assets)
    910


    QUEUE TIMES (time jobs spend in queue)
    count                       910
    mean     0 days 00:00:59.290003
    std      0 days 00:00:09.577545
    min      0 days 00:00:20.515242
    25%      0 days 00:01:00.394103
    50%      0 days 00:01:01.917222
    75%      0 days 00:01:03.416856
    max      0 days 00:01:05.078041
    dtype: object


    PROCESS TIMES (time jobs spend processing)
    count                       910
    mean     0 days 00:00:00.514161
    std      0 days 00:00:00.036910
    min      0 days 00:00:00.313869
    25%      0 days 00:00:00.493621
    50%      0 days 00:00:00.516982
    75%      0 days 00:00:00.535746
    max      0 days 00:00:00.625810
    dtype: object


    WAIT TIMES (time jobs spend waiting to process)
    count                       910
    mean     0 days 00:00:59.804165
    std      0 days 00:00:09.578807
    min      0 days 00:00:20.940050
    25%      0 days 00:01:00.880434
    50%      0 days 00:01:02.427082
    75%      0 days 00:01:03.921606
    max      0 days 00:01:05.549530
    dtype: object


    BYTES PER ASSET (bytes transcoded per asset)
    count       910
    mean     277880
    std           0
    min      277880
    25%      277880
    50%      277880
    75%      277880
    max      277880
    dtype: float64

    BPS: 2523206.55183 bytes written per second (avg)
    APS: 9.08020207221 assets processed per second (avg)
```

In a true performance "test," the number of workers would be standardized and these metrics would have fail conditions
depending on business needs e.g.

- no customer should wait longer than 3 minutes for an asset to complete
- bytes written per second should exceed 2000000 (2 MBps)
- no single asset should exceed processing time of 1s


## Requirements

- unix operating system
- python 2.7
- all python packages in requirements.txt (installable by `pip install -r requirements.txt`)
- redis & redis-server


## How to run the demo

First, start the web app. CD into the project root if you are not there already and run:

    # Run the app
    ./app.py

You also need to ensure the redis server is running and listening on the default port (6379):

    # Start the redis server
    redis-server

Then you can start any number of queue workers to perform the transcoding background tasks:

    # Start the redis queue workers
    rqworker default

Finally, run the script to report on the transcoding performance:

    ./run_perf_test.py

Feel free to tweak the numbers.








