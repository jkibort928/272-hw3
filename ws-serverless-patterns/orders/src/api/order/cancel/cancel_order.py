import simplejson as json
import os
import boto3
from botocore.exceptions import ClientError
from utils import get_order

order_table = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')


def cancel_order(event):
    user_id = event['requestContext']['authorizer']['claims']['sub']
    order_id = event['pathParameters']['orderId']

    table = dynamodb.Table(order_table)

    try:
        table.update_item(
            Key={
                'userId': user_id,
                'orderId': order_id
            },
            UpdateExpression='SET #data.#status = :status',
            ConditionExpression='attribute_exists(userId) AND attribute_exists(orderId) AND #data.#status = :placed',
            ExpressionAttributeNames={
                '#data': 'data',
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': 'CANCELLED',
                ':placed': 'PLACED'
            }
        )
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'ConditionalCheckFailedException':
            raise Exception(
                f"Cannot cancel Order {order_id}. Please check if the order exists and the status is PLACED."
            )
        raise Exception(
            f"Error occurred: {exc.response['Error']['Code']}: {exc.response['Error']['Message']}"
        )

    return get_order(user_id, order_id)


def lambda_handler(event, context):
    try:
        cancelled = cancel_order(event)
        return {
            "statusCode": 200,
            "headers": {},
            "body": json.dumps(cancelled)
        }
    except Exception as err:
        raise Exception(str(err))
