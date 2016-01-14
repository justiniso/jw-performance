import requests
import uuid


def test_upload(hostname, large_file):
    """
    Test uploading an image succeeds and returns correct data

    :param hostname: The hostname under test (this fixture is automatically injected by pytest)
    :param large_file: A large-ish filename (this fixture is automatically injected by pytest)
    """
    with open(large_file, 'r') as f:
        resp = requests.post(hostname + '/images',
                             data={'user_id': 'test-user-{}'.format(uuid.uuid4())},
                             files={'file': ('bridge.jpeg', f)})

    assert resp.status_code == 200, 'Error uploading an image; this should not fail: {}'.format(resp.content)
    data = resp.json()

    assert data.get('id'), 'Uploaded image did not respond with an ID'
    assert data.get('location'), 'Uploaded image did not respond with a location'

    # Clean up test data and delete the image
    requests.delete(hostname + '/image/{}'.format(data['id']))
