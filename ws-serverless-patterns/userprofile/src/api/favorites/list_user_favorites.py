import os
import boto3
import json
import logging
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

favorites_table = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')


def list_favorites(event: dict):
    # An API Gateway proxy event - this read is synchronous, unlike the writes.
    user_id = event['requestContext']['authorizer']['claims']['sub']

    table = dynamodb.Table(favorites_table)
    response = table.query(
        KeyConditionExpression=Key('user_id').eq(user_id)
    )

    favorites = response['Items']
    for favorite in favorites:
        favorite.pop('user_id', None)

    return favorites


def lambda_handler(event, context):
    try:
        favorites = list_favorites(event)
        return {
            "statusCode": 200,
            "headers": {},
            "body": json.dumps({"favorites": favorites})
        }
    except Exception:
        logger.exception("Failed to list favorites")
        raise
