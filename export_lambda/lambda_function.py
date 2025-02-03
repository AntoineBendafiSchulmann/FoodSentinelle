import os
import json
import boto3
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")

TABLE_NAME = os.environ.get("TABLE_NAME", "Reviews")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "fooodsentinelle-export-bucket-json")
DATA_KEY = os.environ.get("DATA_KEY", "reviews_export.json")
MANIFEST_KEY = os.environ.get("MANIFEST_KEY", "reviews_export.manifest")

def decimal_to_float(value):
    if isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, list):
        return [decimal_to_float(v) for v in value]
    elif isinstance(value, dict):
        return {k: decimal_to_float(v) for k, v in value.items()}
    else:
        return value

def flatten_item(item, parent_key="", sep="_"):
    flattened = {}
    for k, v in item.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            sub_flat = flatten_item(v, new_key, sep)
            for sub_k, sub_v in sub_flat.items():
                flattened[sub_k] = sub_v
        elif isinstance(v, list):
            flattened[new_key] = json.dumps(v)  
        else:
            flattened[new_key] = v
    return flattened

def lambda_handler(event, context):
    table = dynamodb.Table(TABLE_NAME)
    all_items = []
    resp = table.scan()
    all_items.extend(resp.get("Items", []))
    while "LastEvaluatedKey" in resp:
        resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        all_items.extend(resp.get("Items", []))

    clean_items = [decimal_to_float(it) for it in all_items]
    flattened_list = [flatten_item(it) for it in clean_items]

    # 1) On écrit le fichier JSON principal (données aplanies)
    data_json = json.dumps(flattened_list, indent=2)
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=DATA_KEY,
        Body=data_json,
        ContentType="application/json"
    )

    manifest_content = {
        "fileLocations": [
            {
                "URIPrefixes": [
                    f"s3://{BUCKET_NAME}/{DATA_KEY}"
                ]
            }
        ],
        "globalUploadSettings": {
            "format": "JSON",
            "containsHeader": "false"
        }
    }
    manifest_json = json.dumps(manifest_content, indent=2)
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=MANIFEST_KEY,
        Body=manifest_json,
        ContentType="application/json"
    )

    return {
        "statusCode": 200,
        "body": (
            f"Data => s3://{BUCKET_NAME}/{DATA_KEY}\n"
            f"Manifest => s3://{BUCKET_NAME}/{MANIFEST_KEY}\n"
            f"Total items: {len(flattened_list)}"
        )
    }
