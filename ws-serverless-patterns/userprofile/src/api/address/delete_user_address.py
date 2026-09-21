import os
import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

addresses_table = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')


def delete_address(event: dict):
    detail = event['detail']
    user_id = detail['userId']
    address_id = detail['addressId']

    if not address_id:
        raise Exception("addressId is required to delete an address")

    table = dynamodb.Table(addresses_table)
    table.delete_item(
        Key={
            'user_id': user_id,
            'address_id': address_id
        }
    )

    logger.info("Deleted address %s for user %s", address_id, user_id)
    return address_id


def lambda_handler(event, context):
    logger.info("Processing event: %s", json.dumps(event))
    try:
        return delete_address(event)
    except Exception:
        logger.exception("Failed to delete address")
        raise
