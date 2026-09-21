import os
import boto3
import json
import uuid
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

addresses_table = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')


def add_address(event: dict):
    # An EventBridge event, not an API Gateway proxy event - the payload the API
    # built lives under 'detail'.
    detail = event['detail']
    user_id = detail['userId']
    address_id = str(uuid.uuid4())

    table = dynamodb.Table(addresses_table)
    table.put_item(
        Item={
            'user_id': user_id,
            'address_id': address_id,
            'line1': detail['line1'],
            'line2': detail.get('line2', ''),
            'city': detail['city'],
            'stateProvince': detail['stateProvince'],
            'postal': detail['postal'],
        }
    )

    logger.info("Added address %s for user %s", address_id, user_id)
    return address_id


def lambda_handler(event, context):
    logger.info("Processing event: %s", json.dumps(event))
    try:
        return add_address(event)
    except Exception:
        # Re-raise so EventBridge sees the failure and retries.
        logger.exception("Failed to add address")
        raise
