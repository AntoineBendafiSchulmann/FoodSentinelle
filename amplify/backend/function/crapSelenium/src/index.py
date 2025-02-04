import uuid
import time
from decimal import Decimal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import boto3
import json

from src.yelp_api import get_restaurants_by_location
from src.db import put_restaurant, put_review

def get_secret():
    secret_name = "yelp_api_key"
    region_name = "eu-west-3"
    client = boto3.client("secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response["SecretString"])

    return secret.get("yelp_api_key", "")

def get_selenium_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service("/opt/chromedriver")

    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_reviews_selenium(yelp_alias_or_slug, max_reviews=5):
    if not yelp_alias_or_slug:
        return []

    url = f"https://www.yelp.com/biz/{yelp_alias_or_slug}"
    driver = get_selenium_driver()
    reviews_data = []

    try:
        driver.get(url)
        time.sleep(4)

        review_elements = driver.find_elements(By.XPATH, '//p[contains(@class, "comment__09f24__D0cxf")]')
        rating_elements = driver.find_elements(By.XPATH, './/div[@role="img" and contains(@aria-label,"star rating")]')
        date_elements = driver.find_elements(By.XPATH, './/span[contains(@class, "css-1e4fdj9")]')

        for i in range(min(max_reviews, len(review_elements))):
            review_text = review_elements[i].text if review_elements[i].text else ""
            rating_value = rating_elements[i].get_attribute("aria-label").split(" ")[0] if i < len(
                rating_elements) else "0"
            time_created = date_elements[i].text if i < len(date_elements) else ""

            reviews_data.append({
                "text": review_text,
                "rating": Decimal(rating_value),
                "time_created": time_created
            })
    finally:
        driver.quit()

    return reviews_data


def lambda_handler(event, context):
    location = event.get("location", "Paris")
    api_key = get_secret()
    print(f"Fetching restaurants for location: {location}")

    restaurants = get_restaurants_by_location(location=location, limit=10, api_key=api_key)
    print(f"Found {len(restaurants)} restaurants.")

    for r in restaurants:
        restaurant_id = r["id"]
        alias = r.get("alias", "")
        name = r.get("name", "")
        address = ", ".join(r.get("location", {}).get("display_address", []))
        rating = Decimal(str(r.get("rating", 0)))

        put_restaurant(
            restaurant_id=restaurant_id,
            name=name,
            address=address,
            rating=rating,
            yelp_id=restaurant_id
        )
        print(f"[+] Inserted Restaurant: {name} (ID: {restaurant_id})")

        reviews = scrape_reviews_selenium(alias, max_reviews=5) if alias else []
        print(f"      -> Found {len(reviews)} reviews for {name}.")

        for rev in reviews:
            put_review(
                review_id=str(uuid.uuid4()),
                restaurant_id=restaurant_id,
                text=rev.get("text", ""),
                rating=rev.get("rating", Decimal("0")),
                time_created=rev.get("time_created", "")
            )
            print(f"    [++] Inserted Review.")

    print("Done inserting data into DynamoDB.")
    return {"statusCode": 200, "body": "Success"}