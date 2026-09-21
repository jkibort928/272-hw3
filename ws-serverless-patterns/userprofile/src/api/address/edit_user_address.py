import os
import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

addresses_table = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')


def edit_address(event: dict):
    detail = event['detail']
    user_id = detail['userId']
    address_id = detail['addressId']

    if not address_id:
        raise Exception("addressId is required to edit an address")

    table = dynamodb.Table(addresses_table)
    table.update_item(
        Key={
            'user_id': user_id,
            'address_id': address_id
        },
        UpdateExpression=(
            'SET line1 = :line1, line2 = :line2, city = :city, '
            'stateProvince = :stateProvince, postal = :postal'
        ),
        # Only update what already exists; an update for a missing address is a
        # bug worth surfacing, not a silent insert.
        ConditionExpression='attribute_exists(user_id) AND attribute_exists(address_id)',
        ExpressionAttributeValues={
            ':line1': detail['line1'],
            ':line2': detail.get('line2', ''),
            ':city': detail['city'],
            ':stateProvince': detail['stateProvince'],
            ':postal': detail['postal'],
        }
    )

    logger.info("Updated address %s for user %s", address_id, user_id)
    return address_id


def lambda_handler(event, context):
    logger.info("Processing event: %s", json.dumps(event))
    try:
        return edit_address(event)
    except Exception:
        logger.exception("Failed to edit address")
        raise
