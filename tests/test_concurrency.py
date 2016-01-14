import datetime
import random
from multiprocessing import Process

import requests
import uuid
import time


PROCESS_TIMEOUT = 20
TOTAL_TIMEOUT = 30


def run_and_wait_for_job_complete(hostname, large_file, img_id):

    action = random.choice(('resize', 'crop', 'transcode'))

    if action == 'resize':
        resp = requests.put(hostname + '/image/{}'.format(img_id), data={'action': 'resize', 'size': '5000,5000'})

    elif action == 'crop':
        resp = requests.put(hostname + '/image/{}'.format(img_id), data={'action': 'crop', 'box': '50,50,2100,2000'})

    elif action == 'transcode':
        resp = requests.put(hostname + '/image/{}'.format(img_id), data={'action': 'transcode', 'extension': 'bmp'})

    job_id = resp.json()['job_id']

    wait_for_job_done(hostname + '/job/{}'.format(job_id))


def wait_for_job_done(url):
    max_wait = PROCESS_TIMEOUT
    start = datetime.datetime.now()
    time_elapsed = 0
    finished = False
    status = None

    while time_elapsed < max_wait:
        if time_elapsed > 0:
            time.sleep(3)

        resp = requests.get(url)
        status = resp.json()['status']
        if status == 'done':
            finished = True
            break

        time_elapsed = (datetime.datetime.now() - start).total_seconds()

    assert finished, \
        'The resize job never completed but should have within the allotted time. Last status was "{}" and ' \
        'url was "{}"'.format(status, url)


def test_job_states(hostname, large_file):
    """
    Tests that you can simultaneously perform image actions on a single image and the application will correctly perform
    them in order

    :param hostname: The hostname under test (this fixture is automatically injected by pytest)
    :param large_file: A large-ish filename (this fixture is automatically injected by pytest)
    """
    with open(large_file, 'r') as f:
        resp = requests.post(hostname + '/images',
                             data={'user_id': 'test-user-{}'.format(uuid.uuid4())},
                             files={'file': ('bridge.jpeg', f)})

    img_id = resp.json()['id']

    concurrent_uploads = 10
    processes = [Process(target=run_and_wait_for_job_complete, args=(hostname, large_file, img_id))
                 for _ in range(concurrent_uploads)]

    for p in processes:
        p.start()

    for p in processes:
        p.join(timeout=TOTAL_TIMEOUT)

    # Clean up the data
    requests.delete(hostname + '/image/{}'.format(img_id))
