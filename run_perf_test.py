#!/usr/bin/env bash
import datetime
import os
import time

import requests
import pandas
import polling

from track import rclient


def parse_time(seconds):
    return datetime.timedelta(seconds=float(seconds))


def purge_data():
    """Wipe all redis keys; this is just a shortcut and we may want to store these in a more permanent
    place in the future
    """
    print 'Purging data...'
    rclient.delete('asset.time.queue', 'asset.time.process', 'asset.time.wait', 'asset.bytes', 'asset.count.completed')


def generate_data():
    """Generate the performance test data by triggering the events which will report their metrics"""
    # We need to generate
    print 'Generating data...'

    # Make some fake data; essentially, create a giant list of user IDs to represent each upload
    user_ids = [1 for _ in range(100)] + [2 for _ in range(200)] + [3 for _ in range(50)] + [4 for _ in range(10)]
    upload_image = os.path.join(os.path.dirname(__file__), 'bunny.jpg')

    for user_id in user_ids:
        with open(upload_image, 'rb') as f:
            resp = requests.post(
                'http://localhost:5000/upload',
                data={'user_id': user_id},
                files={'file': ('bunny.jpg', f)})

            assert resp.status_code == 200, 'Error! {} status code: {}'.format(resp.status_code, resp.content)

    resp = requests.post('http://localhost:5000/process')
    assert resp.status_code == 200, 'Error! {} status code: {}'.format(resp.status_code, resp.content)

    # Now wait until all assets have been processed before moving on
    try:
        polling.poll(
            lambda: int(rclient.get('asset.count.completed')) >= len(user_ids),
            timeout=600,
            step=1
        )
    except polling.TimeoutException:
        assert False, 'All assets were not processed. Total processed assets were: {}'.format(rclient.get('asset.count.completed'))


def analyze_data(elapsed_time):
    print 'Analyzing data...'

    seconds_elapsed = elapsed_time.total_seconds()
    queue_times = [parse_time(t) for t in rclient.lrange('asset.time.queue', 0, -1)]
    process_times = [parse_time(t) for t in rclient.lrange('asset.time.process', 0, -1)]
    wait_times = [parse_time(t) for t in rclient.lrange('asset.time.wait', 0, -1)]
    bytes_per_asset = [int(metric) for metric in rclient.lrange('asset.bytes', 0, -1)]
    total_completed = int(rclient.get('asset.count.completed'))

    print '\nTOTAL SECONDS (total time elapsed)\n{}\n'.format(seconds_elapsed)
    print '\nTOTAL ASSETS (total number of assets)\n{}\n'.format(total_completed)
    print '\nQUEUE TIMES (time jobs spend in queue)\n{}\n'.format(pandas.Series(queue_times).describe())
    print '\nPROCESS TIMES (time jobs spend processing)\n{}\n'.format(pandas.Series(process_times).describe())
    print '\nWAIT TIMES (time jobs spend waiting to process)\n{}\n'.format(pandas.Series(wait_times).describe())
    print '\nBYTES PER ASSET (bytes transcoded per asset)\n{}\n'.format(pandas.Series(bytes_per_asset).describe())

    assert seconds_elapsed > 0  # No one likes divide by zero errors

    # Computed metrics
    print 'BPS: {} bytes written per second (avg)'.format(sum(bytes_per_asset) / seconds_elapsed)
    print 'APS: {} assets processed per second (avg)'.format(total_completed / seconds_elapsed)


if __name__ == '__main__':
    purge_data()

    start = datetime.datetime.now()
    generate_data()
    end = datetime.datetime.now()

    analyze_data(elapsed_time=end - start)