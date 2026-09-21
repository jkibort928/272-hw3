import json
import logging
import time
import uuid

import pytest
import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# How long to wait for an asynchronous write to land before calling it a failure.
POLL_TIMEOUT_SECONDS = 20
POLL_INTERVAL_SECONDS = 1

address_1 = {
    "line1": "1 Washington Square",
    "line2": "Apt 4",
    "city": "San Jose",
    "stateProvince": "CA",
    "postal": "95192",
}


@pytest.fixture
def api_endpoint(global_config):
    '''Returns the endpoint for the User Profile service'''
    return global_config["ProfileApiEndpoint"]


@pytest.fixture
def user_token(global_config):
    '''Returns the user_token for authentication to the User Profile service'''
    return global_config["user1UserIdToken"]


@pytest.fixture
def auth_headers(user_token):
    return {'Authorization': user_token, 'Content-Type': 'application/json'}


def poll_until(fetch, predicate, description):
    """
    Poll an asynchronous result until it satisfies predicate.

    Writes return 202 before any consumer has run, so reading immediately after
    a write is a race. Every assertion about asynchronous state goes through here.
    """
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    latest = None

    while time.time() < deadline:
        latest = fetch()
        if predicate(latest):
            return latest
        time.sleep(POLL_INTERVAL_SECONDS)

    raise AssertionError(
        f"Timed out after {POLL_TIMEOUT_SECONDS}s waiting for {description}. "
        f"Last value seen: {latest!r}"
    )


def get_addresses(api_endpoint, headers):
    response = requests.get(api_endpoint + '/address', headers=headers)
    assert response.status_code == 200
    return response.json()['addresses']


def get_favorites(api_endpoint, headers):
    response = requests.get(api_endpoint + '/favorite', headers=headers)
    assert response.status_code == 200
    return response.json()['favorites']


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def test_access_address_without_authentication(api_endpoint):
    response = requests.post(api_endpoint + '/address', data=json.dumps(address_1))
    assert response.status_code == 401


def test_access_favorite_without_authentication(api_endpoint):
    response = requests.get(api_endpoint + '/favorite')
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Addresses: API Gateway -> EventBridge -> Lambda -> DynamoDB
# ---------------------------------------------------------------------------

def test_add_address_is_accepted_asynchronously(global_config, api_endpoint, auth_headers):
    response = requests.post(
        api_endpoint + '/address',
        data=json.dumps(address_1),
        headers=auth_headers
    )

    # 202, not 200: the event is on the bus, but nothing has processed it yet.
    assert response.status_code == 202

    # The API cannot return an id, because no consumer has run to assign one.
    # This is the contract difference from the synchronous Orders service.
    body = response.json()
    assert 'addressId' not in body

    addresses = poll_until(
        lambda: get_addresses(api_endpoint, auth_headers),
        lambda items: len(items) == 1,
        "the address to appear after asynchronous processing"
    )

    stored = addresses[0]
    assert stored['line1'] == address_1['line1']
    assert stored['city'] == address_1['city']
    assert stored['postal'] == address_1['postal']
    assert 'user_id' not in stored

    global_config['addressId'] = stored['address_id']


def test_edit_address(global_config, api_endpoint, auth_headers):
    address_id = global_config['addressId']
    updated = dict(address_1, city="Santa Clara", postal="95050")

    response = requests.put(
        api_endpoint + '/address/' + address_id,
        data=json.dumps(updated),
        headers=auth_headers
    )
    assert response.status_code == 202

    poll_until(
        lambda: get_addresses(api_endpoint, auth_headers),
        lambda items: len(items) == 1 and items[0]['city'] == "Santa Clara",
        "the address update to be applied"
    )


def test_delete_address(global_config, api_endpoint, auth_headers):
    address_id = global_config['addressId']

    response = requests.delete(
        api_endpoint + '/address/' + address_id,
        headers=auth_headers
    )
    assert response.status_code == 202

    poll_until(
        lambda: get_addresses(api_endpoint, auth_headers),
        lambda items: len(items) == 0,
        "the address to be removed"
    )


# ---------------------------------------------------------------------------
# Favorites: API Gateway -> SQS -> Lambda -> DynamoDB
# ---------------------------------------------------------------------------

def test_add_favorite_is_accepted_asynchronously(global_config, api_endpoint, auth_headers):
    restaurant_id = str(uuid.uuid4())
    global_config['restaurantId'] = restaurant_id

    response = requests.post(
        api_endpoint + '/favorite',
        data=json.dumps({"restaurantId": restaurant_id}),
        headers=auth_headers
    )

    # Accepted onto the queue; the consumer has not necessarily run.
    assert response.status_code == 202

    favorites = poll_until(
        lambda: get_favorites(api_endpoint, auth_headers),
        lambda items: len(items) == 1,
        "the favorite to appear after asynchronous processing"
    )

    assert favorites[0]['restaurant_id'] == restaurant_id
    assert 'user_id' not in favorites[0]


def test_delete_favorite(global_config, api_endpoint, auth_headers):
    restaurant_id = global_config['restaurantId']

    response = requests.delete(
        api_endpoint + '/favorite/' + restaurant_id,
        headers=auth_headers
    )
    assert response.status_code == 202

    poll_until(
        lambda: get_favorites(api_endpoint, auth_headers),
        lambda items: len(items) == 0,
        "the favorite to be removed"
    )
