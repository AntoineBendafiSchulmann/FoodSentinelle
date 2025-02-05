import json
import boto3
import os
import decimal

dynamodb = boto3.resource("dynamodb")

TABLE_NAME = "Restaurants"
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):

    path = event.get("path", "")
    http_method = event.get("httpMethod", "")
    if path == "/getRestaurant" and http_method == "GET":
        qs = event.get("queryStringParameters") or {}
        restaurant_id = qs.get("id", "")
        if not restaurant_id:
            return response_400("Missing ?id parameter")

        return get_restaurant_by_id(restaurant_id)

    return response_404("Not found")

def get_restaurant_by_id(restaurant_id):

    resp = table.get_item(Key={"restaurant_id": restaurant_id})
    item = resp.get("Item")
    if not item:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": f"Restaurant {restaurant_id} not found"})
        }

    item = decimal_to_float(item)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(item)
    }

def decimal_to_float(obj):
    """
    Convertit récursivement les valeurs decimal.Decimal en float,
    pour permettre l'encodage JSON.
    """
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    elif isinstance(obj, list):
        return [decimal_to_float(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    else:
        return obj

def response_400(message):
    return {
        "statusCode": 400,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message})
    }

def response_404(message):
    return {
        "statusCode": 404,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message})
    }
