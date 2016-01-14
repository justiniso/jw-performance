import datetime
import requests
import uuid
import time


def test_job_states(hostname, large_file):
    """
    Test that after requesting an action, the job will update and eventually wind up in status "done"

    :param hostname: The hostname under test (this fixture is automatically injected by pytest)
    :param large_file: A large-ish filename (this fixture is automatically injected by pytest)
    """
    with open(large_file, 'r') as f:
        resp = requests.post(hostname + '/images',
                             data={'user_id': 'test-user-{}'.format(uuid.uuid4())},
                             files={'file': ('bridge.jpeg', f)})

    img_id = resp.json()['id']

    # Send a resize request and use the job_id to check for current state
    resp = requests.put(hostname + '/image/{}'.format(img_id), data={'action': 'resize', 'size': '50,50'})
    job_id = resp.json()['job_id']
    wait_for_job_done(hostname + '/job/{}'.format(job_id))

    # Send a crop request and use the job_id to check for current state
    resp = requests.put(hostname + '/image/{}'.format(img_id), data={'action': 'crop', 'box': '50,50,100,100'})
    job_id = resp.json()['job_id']
    wait_for_job_done(hostname + '/job/{}'.format(job_id))

    # Send a transcode request and use the job_id to check for current state
    resp = requests.put(hostname + '/image/{}'.format(img_id), data={'action': 'transcode', 'extension': 'bmp'})
    job_id = resp.json()['job_id']
    wait_for_job_done(hostname + '/job/{}'.format(job_id))

    # Clean up test data and delete the image
    requests.delete(hostname + '/image/{}'.format(img_id))


def wait_for_job_done(url):
    # Wait for the job to be finished (max of 5 seconds; if it took longer than 5 secs to complete, there is a problem)
    max_wait = 5
    start = datetime.datetime.now()
    time_elapsed = 0
    finished = False
    status = None

    while time_elapsed < max_wait:
        if time_elapsed > 0:
            time.sleep(0.3)

        resp = requests.get(url)
        status = resp.json()['status']
        if status == 'done':
            finished = True
            break

        time_elapsed = (datetime.datetime.now() - start).total_seconds()

    assert finished, \
        'The resize job never completed but should have within the allotted time. Last status was "{}"'.format(status)
