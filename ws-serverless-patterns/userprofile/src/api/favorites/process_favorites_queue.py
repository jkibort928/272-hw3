import os
import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

favorites_table = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')


def add_favorite(user_id: str, restaurant_id: str):
    table = dynamodb.Table(favorites_table)
    table.put_item(
        Item={
            'user_id': user_id,
            'restaurant_id': restaurant_id
        }
    )
    logger.info("Favorite restaurant %s saved for user %s", restaurant_id, user_id)


def delete_favorite(user_id: str, restaurant_id: str):
    table = dynamodb.Table(favorites_table)
    table.delete_item(
        Key={
            'user_id': user_id,
            'restaurant_id': restaurant_id
        }
    )
    logger.info("Favorite restaurant %s removed for user %s", restaurant_id, user_id)


def process_event(event: dict):
    # An SQS event carries a batch; one API call produced each record.
    for record in event['Records']:
        restaurant_id = record['body']
        attributes = record['messageAttributes']
        user_id = attributes['UserId']['stringValue']
        command_name = attributes['CommandName']['stringValue']

        if not restaurant_id:
            raise Exception("restaurant_id is required")

        if command_name == "AddFavorite":
            add_favorite(user_id, restaurant_id)
        elif command_name == "DeleteFavorite":
            delete_favorite(user_id, restaurant_id)
        else:
            raise Exception(f"Command {command_name} not recognized")


def lambda_handler(event, context):
    logger.info("Processing event: %s", json.dumps(event))
    try:
        process_event(event)
    except Exception:
        # Re-raise so SQS returns the message to the queue for retry.
        logger.exception("Failed to process favorites queue message")
        raise
