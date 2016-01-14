import requests
import uuid


def test_action_flow(hostname, large_file):
    """
    Test that applying each action to an image reflects that action in the image's "action" data

    Actions are made by making a request to:

        /image/<image_id>

    with a payload of:

        {'action': 'resize', 'size': '50,50'}
        {'action': 'crop', 'box': '0,50,900,200'}
        {'action': 'transcode', 'extension': 'png'}

    depending on which action you wish to take.

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

    # Current actions on the image should only be 'upload'
    resp = requests.get(hostname + '/image/{}'.format(data['id']))
    assert resp.json()['actions'] == ['upload']

    # Resize the image and check that the actions now include a resize
    resp = requests.put(hostname + '/image/{}'.format(data['id']), data={'action': 'resize', 'size': '50,50'})
    assert resp.status_code == 200
    resp = requests.get(hostname + '/image/{}'.format(data['id']))
    assert resp.json()['actions'] == ['upload', 'resize']

    # Crop the image and check that the actions include a crop
    resp = requests.put(hostname + '/image/{}'.format(data['id']), data={'action': 'crop', 'box': '0,50,900,200'})
    assert resp.status_code == 200
    resp = requests.get(hostname + '/image/{}'.format(data['id']))
    assert resp.json()['actions'] == ['upload', 'resize', 'crop']

    # Transcode the image, check that transcode is now in actions
    resp = requests.put(hostname + '/image/{}'.format(data['id']), data={'action': 'transcode', 'extension': 'png'})
    assert resp.status_code == 200
    resp = requests.get(hostname + '/image/{}'.format(data['id']))
    assert resp.json()['actions'] == ['upload', 'resize', 'crop', 'transcode']

    # Clean up test data and delete the image
    requests.delete(hostname + '/image/{}'.format(data['id']))
