import uuid

import requests
import polling


def test_serve_cropped_image(hostname, large_file):
    """
    Test that the correct image is served after cropped

    :param hostname: The hostname under test (this fixture is automatically injected by pytest)
    :param large_file: A large-ish filename (this fixture is automatically injected by pytest)
    """
    with open(large_file, 'r') as f:
        resp = requests.post(hostname + '/images',
                             data={'user_id': 'test-user-{}'.format(uuid.uuid4())},
                             files={'file': ('bridge.jpeg', f)})

    img_id = resp.json()['id']

    # Get the original size
    download = requests.get(hostname + '/serve/{}'.format(img_id))
    original_size = download.headers['content-length']

    # Resize the image
    resp = requests.put(hostname + '/image/{}'.format(img_id), data={'action': 'crop', 'box': '25,25,900,200'})
    job_id1 = resp.json()['job_id']

    resp = requests.get(hostname + '/image/{}'.format(img_id))
    assert resp.json()['last_job'] == job_id1

    # Wait for the job to be done
    polling.poll(
        lambda: requests.get(hostname + '/image/{}'.format(img_id)),
        check_success=lambda response: response.json()['last_job_state'] == 'done',
        timeout=5,
        step=1)

    # Download the image, ensure it was actually cropped
    download = requests.get(hostname + '/serve/{}'.format(img_id))
    assert download.headers['content-length'] < original_size
    assert download.headers['content-type'] == 'image/jpeg'

    # Clean up the data
    requests.delete(hostname + '/image/{}'.format(img_id))


