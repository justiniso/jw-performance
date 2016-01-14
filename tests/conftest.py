"""
This module is used by pytest to generate the fixtures at runtime
"""
import pytest
import os
from app import TEST_HOST, TEST_PORT

# Use this hostname for all tests
FQDN = 'http://{}:{}'.format(TEST_HOST, TEST_PORT)


@pytest.fixture
def hostname(*args, **kwargs):
    return FQDN


@pytest.fixture
def large_file(*args, **kwargs):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bridge.jpeg')