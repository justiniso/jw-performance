import uuid

import requests
import polling


def test_serve_transcoded_image(hostname, large_file):
    """
    Test that the correct image content type is served after transcoding

    :param hostname: The hostname under test (this fixture is automatically injected by pytest)
    :param large_file: A large-ish filename (this fixture is automatically injected by pytest)
    """
    with open(large_file, 'r') as f:
        resp = requests.post(hostname + '/images',
                             data={'user_id': 'test-user-{}'.format(uuid.uuid4())},
                             files={'file': ('bridge.jpeg', f)})

    img_id = resp.json()['id']

    # Resize the image
    resp = requests.put(hostname + '/image/{}'.format(img_id), data={'action': 'transcode', 'extension': 'png'})
    job_id = resp.json()['job_id']

    resp = requests.get(hostname + '/image/{}'.format(img_id))
    assert resp.json()['last_job'] == job_id

    # Wait for the job to be done
    polling.poll(
        lambda: requests.get(hostname + '/image/{}'.format(img_id)),
        check_success=lambda response: response.json()['last_job_state'] == 'done',
        timeout=5,
        step=1)

    # Download the image, ensure it is smaller after resize
    download = requests.get(hostname + '/serve/{}'.format(img_id))
    assert download.headers['content-type'] == 'image/png'

    # Clean up the data
    requests.delete(hostname + '/image/{}'.format(img_id))


