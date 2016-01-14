import requests
import uuid


def test_crop_validation(hostname, large_file):
    """
    Test edge cases of cropping an image

    :param hostname: The hostname under test (this fixture is automatically injected by pytest)
    :param large_file: A large-ish filename (this fixture is automatically injected by pytest)
    """
    with open(large_file, 'r') as f:
        resp = requests.post(hostname + '/images',
                             data={'user_id': 'test-user-{}'.format(uuid.uuid4())},
                             files={'file': ('bridge.jpeg', f)})

    img_id = resp.json()['id']

    bad_payloads = (
        {'action': 'crop', 'box': '50'},
        {'action': 'crop', 'box': ''},
        {'action': 'crop', 'size': '20,20'}
    )
    for bad_payload in bad_payloads:
        resp = requests.put(hostname + '/image/{}'.format(img_id), data=bad_payload)
        assert resp.status_code == 400, 'Request should have failed but did not with payload: {}'.format(bad_payload)
        assert resp.json()['description'].startswith('Invalid bounding box')

    # Clean up test data and delete the image
    requests.delete(hostname + '/image/{}'.format(img_id))
