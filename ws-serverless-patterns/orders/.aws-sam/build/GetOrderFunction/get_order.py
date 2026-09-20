import os
import boto3
import json
from decimal import Decimal

orders_table = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def get_order(event: dict):
    order_id = event['pathParameters']['orderId']
    user_id = event['requestContext']['authorizer']['claims']['sub']

    table = dynamodb.Table(orders_table)

    response = table.get_item(
        Key={
            'orderId': order_id,
            'userId': user_id
        }
    )

    item = response.get('Item')

    if not item:
        return None

    return item['data']


def lambda_handler(event, context):
    try:
        order = get_order(event)

        if order is None:
            return {
                "statusCode": 404,
                "headers": {},
                "body": json.dumps({
                    "message": "Order not found"
                })
            }

        return {
            "statusCode": 200,
            "headers": {},
            "body": json.dumps(order, cls=DecimalEncoder)
        }

    except Exception:
        raise
