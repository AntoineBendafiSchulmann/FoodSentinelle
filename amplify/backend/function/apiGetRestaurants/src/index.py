import json
import boto3
import os
import decimal

dynamodb = boto3.resource("dynamodb")

table = dynamodb.Table("Restaurants")

def handler(event, context):
    path = event.get("path", "")
    http_method = event.get("httpMethod", "")

    if path == "/restaurants" and http_method == "GET":
        return get_restaurants()

    elif path.startswith("/restaurants/") and http_method == "GET":
        parts = path.split("/")
        if len(parts) == 3:
            rid = parts[2]
            return get_restaurant_by_id(rid)
        else:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "Invalid path format"}),
                "headers": {"Content-Type": "application/json"}
            }

    return {
        "statusCode": 404,
        "body": json.dumps({"message": "Not found"}),
        "headers": {"Content-Type": "application/json"}
    }

def get_restaurants():
    resp = table.scan()
    items = resp.get("Items", [])
    items = decimal_to_float(items)
    return {
        "statusCode": 200,
        "body": json.dumps(items),
        "headers": {"Content-Type": "application/json"}
    }

def get_restaurant_by_id(restaurant_id):
    resp = table.get_item(Key={"restaurant_id": restaurant_id})
    item = resp.get("Item")
    if not item:
        return {
            "statusCode": 404,
            "body": json.dumps({"message": f"Restaurant {restaurant_id} not found"}),
            "headers": {"Content-Type": "application/json"}
        }
    item = decimal_to_float(item)
    return {
        "statusCode": 200,
        "body": json.dumps(item),
        "headers": {"Content-Type": "application/json"}
    }

def decimal_to_float(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    elif isinstance(obj, list):
        return [decimal_to_float(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    else:
        return obj
