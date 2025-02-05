import json
import time
import uuid
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


# ------------------------------
# CONFIG
# ------------------------------
REGION_NAME = "eu-west-3"
RESTAURANTS_TABLE_NAME = "Restaurants"
REVIEWS_TABLE_NAME = "Reviews"
SECRET_NAME = "yelp_api_key"  # Le nom (ARN) du secret dans AWS Secrets Manager
CHROME_BINARY_PATH = "/opt/bin/headless-chromium"
CHROME_DRIVER_PATH = "/opt/bin/chromedriver"

# ------------------------------
# Clients AWS
# ------------------------------
dynamodb = boto3.resource("dynamodb", region_name=REGION_NAME)
restaurants_table = dynamodb.Table(RESTAURANTS_TABLE_NAME)
reviews_table = dynamodb.Table(REVIEWS_TABLE_NAME)
secrets_client = boto3.client("secretsmanager", region_name=REGION_NAME)

# ------------------------------
# FONCTIONS DynamoDB
# ------------------------------
def put_restaurant(restaurant_id, name, address, rating):
    """
    Insert or update a record in 'Restaurants' table.
    """
    item = {
        "restaurant_id": restaurant_id,
        "name": name,
        "address": address,
        "rating": rating
    }
    restaurants_table.put_item(Item=item)

def put_review(review_id, restaurant_id, text, rating, time_created):
    """
    Insert or update a record in 'Reviews' table.
    """
    item = {
        "review_id": review_id,
        "restaurant_id": restaurant_id,
        "text": text,
        "rating": rating,
        "time_created": time_created
    }
    reviews_table.put_item(Item=item)

# ------------------------------
# Secrets Manager : Récupérer la clé Yelp
# ------------------------------
def get_yelp_api_key():
    try:
        resp = secrets_client.get_secret_value(SecretId=SECRET_NAME)
        raw = resp["SecretString"]
        # Si jamais le secret est stocké en JSON, on peut parser
        # Dans l'exemple suivant, on suppose juste que c'est une chaîne brute
        return raw
    except ClientError as e:
        print(f"Erreur lors de la récupération du secret {SECRET_NAME} : {e}")
        raise

# ------------------------------
# Selenium : Configuration
# ------------------------------
def get_selenium_driver():
    """
    Initialise un WebDriver Chrome (headless).
    Assure-toi que /opt/chromedriver et /opt/headless-chromium existent dans la Layer.
    """
    chrome_options = Options()
    chrome_options.binary_location = CHROME_BINARY_PATH
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Utiliser le chromedriver inclus dans la Layer
    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# ------------------------------
# Scraper Yelp (Selenium)
# ------------------------------
def scrape_yelp_business(alias):
    """
    Ex : alias = "le-sushi-bar-paris" => https://www.yelp.com/biz/le-sushi-bar-paris
    Scrap les reviews, rating, etc.
    """
    if not alias:
        return []

    url = f"https://www.yelp.com/biz/{alias}"
    driver = get_selenium_driver()
    reviews_data = []

    try:
        driver.get(url)
        time.sleep(4)  # Laisse le temps à la page de charger

        # Ex de récupération de reviews par XPATH
        review_elements = driver.find_elements(By.XPATH, '//p[contains(@class,"comment__09f24__D0cxf")]')
        rating_elements = driver.find_elements(By.XPATH, './/div[@role="img" and contains(@aria-label,"star rating")]')
        date_elements = driver.find_elements(By.XPATH, './/span[contains(@class, "css-1e4fdj9")]')

        max_reviews = min(len(review_elements), 5)
        for i in range(max_reviews):
            text = review_elements[i].text or ""
            rating_str = "0"
            if i < len(rating_elements):
                aria_label = rating_elements[i].get_attribute("aria-label")
                if aria_label:
                    rating_str = aria_label.split(" ")[0]  # "4" if "4 star rating"

            date_str = date_elements[i].text if i < len(date_elements) else ""

            reviews_data.append({
                "text": text,
                "rating": Decimal(rating_str),
                "time_created": date_str
            })
    finally:
        driver.quit()

    return reviews_data

# ------------------------------
# Handler principal
# ------------------------------
def lambda_handler(event, context):
    """
    1. Récupère la clé Yelp (facultatif, si vous voulez aussi appeler l'API Yelp)
    2. Scrap en Selenium la page Yelp d'un business
    3. Stocke dans DynamoDB
    """
    # Param dans 'event', ex: event = {"alias": "le-sushi-bar-paris"}
    alias = event.get("alias", "le-sushi-bar-paris")
    print(f"Scraping Yelp alias: {alias}")

    # (Facultatif) : Récupération de la clé Yelp
    # yelp_key = get_yelp_api_key()
    # ... vous pourriez l'utiliser pour faire un call API, etc.

    # Scrap
    reviews = scrape_yelp_business(alias)
    print(f"Found {len(reviews)} reviews.")

    # Enregistrez par ex. le restaurant
    # (Ici, on a besoin d'un 'restaurant_id' unique)
    # Mettez un ID fixe ou construisez-en un
    rest_id = str(uuid.uuid4())
    put_restaurant(
        restaurant_id=rest_id,
        name=f"Fake Restaurant from alias {alias}",
        address="Paris, 75000",
        rating=Decimal("0")
    )

    # Enregistrez les reviews
    for rev in reviews:
        rev_id = str(uuid.uuid4())
        put_review(
            review_id=rev_id,
            restaurant_id=rest_id,
            text=rev["text"],
            rating=rev["rating"],
            time_created=rev["time_created"]
        )
        print(f"Inserted review {rev_id}")

    return {
        "statusCode": 200,
        "body": f"Scraped {len(reviews)} reviews for alias '{alias}'."
    }

if __name__ == "__main__":
    # Test local
    test_event = {"alias": "le-sushi-bar-paris"}
    print(lambda_handler(test_event, None))
