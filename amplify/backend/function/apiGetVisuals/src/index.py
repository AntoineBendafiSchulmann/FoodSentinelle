import json
import boto3
import os
import decimal

s3_client = boto3.client("s3")

def handler(event, context):
    path = event.get("path", "")
    http_method = event.get("httpMethod", "")

    if path == "/visuals" and http_method == "GET":
        qs = event.get("queryStringParameters") or {}
        file_key = qs.get("file", "")
        return get_presigned_url_with_prefix(file_key)

    return {
        "statusCode": 404,
        "body": json.dumps({"message": "Not found"}),
        "headers": {"Content-Type": "application/json"}
    }

def find_s3_object_with_prefix(bucket, prefix):
    resp = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    if "Contents" not in resp:
        return None
    for obj in resp["Contents"]:
        key = obj["Key"]
        if key == prefix:
            return key
        if key.startswith(prefix + "_"):
            return key
    return None

def get_presigned_url_with_prefix(file_key):
    bucket_name = os.environ.get("VISUALS_BUCKET", "foodsentinelle-charts-2025")
    if not file_key:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing ?file= param"}),
            "headers": {"Content-Type": "application/json"}
        }

    matched_key = find_s3_object_with_prefix(bucket_name, file_key)
    if not matched_key:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": f"No matching object for prefix {file_key}"}),
            "headers": {"Content-Type": "application/json"}
        }

    try:

        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": matched_key},
            ExpiresIn=3600
        )
        return {
            "statusCode": 200,
            "body": json.dumps({"url": url}),
            "headers": {"Content-Type": "application/json"}
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
