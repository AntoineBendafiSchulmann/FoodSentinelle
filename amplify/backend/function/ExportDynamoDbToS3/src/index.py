import os
import json
import boto3
import logging
from decimal import Decimal
from botocore.exceptions import ClientError

# Configuration du logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialisation des clients AWS
dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")

# Variables d'environnement
TABLE_NAME = os.environ.get("TABLE_NAME", "Reviews")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "fooodsentinelle-export-bucket-json")
DATA_KEY = os.environ.get("DATA_KEY", "reviews_export.json")
MANIFEST_KEY = os.environ.get("MANIFEST_KEY", "reviews_export.manifest")


def decimal_to_float(value):
    """
    Convertit récursivement les objets Decimal en float dans une structure donnée.
    """
    if isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, list):
        return [decimal_to_float(v) for v in value]
    elif isinstance(value, dict):
        return {k: decimal_to_float(v) for k, v in value.items()}
    return value


def flatten_item(item, parent_key="", sep="_"):
    """
    Aplati un dictionnaire imbriqué en un dictionnaire à une seule profondeur.
    Pour les listes, celles-ci sont converties en chaîne JSON afin d'éviter des sous-listes.
    """
    flattened = {}
    for key, value in item.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            flattened.update(flatten_item(value, new_key, sep))
        elif isinstance(value, list):
            # Convertir la liste en chaîne JSON pour éviter des structures imbriquées
            flattened[new_key] = json.dumps(value)
        else:
            flattened[new_key] = value
    return flattened


def get_all_items_from_dynamodb(table):
    """
    Récupère l'ensemble des items d'une table DynamoDB en gérant la pagination.
    """
    all_items = []
    try:
        response = table.scan()
        all_items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            all_items.extend(response.get("Items", []))
    except ClientError as e:
        logger.error(f"Erreur lors du scan de la table {table.name}: {e}")
        raise e
    return all_items


def export_to_s3(data, key):
    """
    Exporte des données au format JSON dans un bucket S3.
    """
    try:
        json_data = json.dumps(data, indent=2)
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json_data,
            ContentType="application/json"
        )
        logger.info(f"Export réussi vers s3://{BUCKET_NAME}/{key}")
    except ClientError as e:
        logger.error(f"Erreur lors de l'export vers S3: {e}")
        raise e


def create_manifest():
    """
    Crée un manifest pour QuickSight indiquant l'emplacement du fichier de données.
    """
    manifest = {
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
    return manifest


def handler(event, context):
    """
    Handler de la fonction Lambda qui :
      1. Récupère les données depuis DynamoDB.
      2. Convertit les Decimals en float.
      3. Aplati les dictionnaires imbriqués pour éviter les sous-listes.
      4. Exporte les données aplaties et un manifest vers S3.
    """
    logger.info("Démarrage de la fonction Lambda d'export.")

    # Récupération de la table DynamoDB
    table = dynamodb.Table(TABLE_NAME)

    # Récupération de tous les items
    try:
        items = get_all_items_from_dynamodb(table)
        logger.info(f"{len(items)} items récupérés depuis la table {TABLE_NAME}.")
    except Exception as e:
        logger.error("Échec de la récupération des données depuis DynamoDB.")
        return {
            "statusCode": 500,
            "body": "Erreur lors de la récupération des données DynamoDB."
        }

    # Conversion et aplatissement des items
    try:
        clean_items = [decimal_to_float(item) for item in items]
        flattened_items = [flatten_item(item) for item in clean_items]
    except Exception as e:
        logger.error(f"Erreur lors du traitement des données: {e}")
        return {
            "statusCode": 500,
            "body": "Erreur lors du traitement des données."
        }

    # Export des données aplaties vers S3
    try:
        export_to_s3(flattened_items, DATA_KEY)
    except Exception as e:
        logger.error("Échec de l'export du fichier de données vers S3.")
        return {
            "statusCode": 500,
            "body": "Erreur lors de l'export des données vers S3."
        }

    # Création et export du manifest vers S3
    manifest = create_manifest()
    try:
        export_to_s3(manifest, MANIFEST_KEY)
    except Exception as e:
        logger.error("Échec de l'export du manifest vers S3.")
        return {
            "statusCode": 500,
            "body": "Erreur lors de l'export du manifest vers S3."
        }

    response_body = {
        "data_location": f"s3://{BUCKET_NAME}/{DATA_KEY}",
        "manifest_location": f"s3://{BUCKET_NAME}/{MANIFEST_KEY}",
        "total_items": len(flattened_items)
    }

    logger.info("Export terminé avec succès.")
    return {
        "statusCode": 200,
        "body": json.dumps(response_body)
    }
