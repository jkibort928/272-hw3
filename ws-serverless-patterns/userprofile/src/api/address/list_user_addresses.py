import os
import boto3
import json
import logging
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

addresses_table = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')


def list_addresses(event: dict):
    # An API Gateway proxy event - this read is synchronous, unlike the writes.
    user_id = event['requestContext']['authorizer']['claims']['sub']

    table = dynamodb.Table(addresses_table)
    response = table.query(
        KeyConditionExpression=Key('user_id').eq(user_id)
    )

    addresses = response['Items']
    for address in addresses:
        # The caller already knows who they are; don't echo it back.
        address.pop('user_id', None)

    return addresses


def lambda_handler(event, context):
    try:
        addresses = list_addresses(event)
        return {
            "statusCode": 200,
            "headers": {},
            "body": json.dumps({"addresses": addresses})
        }
    except Exception:
        logger.exception("Failed to list addresses")
        raise
