import os
import boto3

orders_table = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')

def get_order(user_id, order_id):
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
