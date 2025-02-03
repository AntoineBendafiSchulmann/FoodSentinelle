import sys
import uuid
from decimal import Decimal
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

from src.yelp_api import get_restaurants_by_location
from src.db import put_restaurant, put_review

def scrape_reviews_selenium(yelp_alias_or_slug, max_reviews=5):
    reviews_data = []
    if not yelp_alias_or_slug:
        return reviews_data
    url = f"https://www.yelp.com/biz/{yelp_alias_or_slug}"
    driver = webdriver.Chrome()
    try:
        driver.get(url)
        time.sleep(3)
        review_elements = driver.find_elements(By.XPATH, '//p[contains(@class, "comment__09f24__D0cxf")]')
        for element in review_elements[:max_reviews]:
            try:
                review_text = element.text
            except:
                review_text = ""
            try:
                rating_el = element.find_element(By.XPATH, './/div[@role="img" and contains(@aria-label,"star rating")]')
                rating_str = rating_el.get_attribute("aria-label")
                rating_value = rating_str.split(" ")[0]
            except:
                rating_value = "0"
            try:
                date_el = element.find_element(By.XPATH, './/span[contains(@class, "css-1e4fdj9")]')
                time_created = date_el.text
            except:
                time_created = ""
            try:
                rating_decimal = Decimal(rating_value)
            except:
                rating_decimal = Decimal("0")
            reviews_data.append({
                "text": review_text,
                "rating": rating_decimal,
                "time_created": time_created
            })
    finally:
        driver.quit()
    return reviews_data

def main():
    if len(sys.argv) > 1:
        location = sys.argv[1]
    else:
        location = "Paris"
    print(f"Fetching restaurants for location: {location}")
    restaurants = get_restaurants_by_location(location=location, limit=10)
    print(f"Found {len(restaurants)} restaurants.")
    for r in restaurants:
        restaurant_id = r["id"]
        alias = r.get("alias", "")
        name = r.get("name", "")
        address = ""
        if "location" in r and "display_address" in r["location"]:
            address = ", ".join(r["location"]["display_address"])
        rating_float = r.get("rating", 0)
        rating = Decimal(str(rating_float))
        yelp_id = restaurant_id
        put_restaurant(
            restaurant_id=restaurant_id,
            name=name,
            address=address,
            rating=rating,
            yelp_id=yelp_id
        )
        print(f"[+] Inserted Restaurant: {name} (ID: {restaurant_id})")
        if alias:
            print(f"    [*] Scraping reviews for alias: {alias} ...")
            reviews = scrape_reviews_selenium(alias, max_reviews=5)
            print(f"      -> Found {len(reviews)} reviews via Selenium for {name}.")
        else:
            print(f"    [!] No alias found for {name}. Skipping scraping.")
            reviews = []
        for rev in reviews:
            review_id = str(uuid.uuid4())
            text = rev.get("text", "")
            review_rating = rev.get("rating", Decimal("0"))
            time_created = rev.get("time_created", "")
            put_review(
                review_id=review_id,
                restaurant_id=restaurant_id,
                text=text,
                rating=review_rating,
                time_created=time_created
            )
            print(f"    [++] Inserted Review: {review_id}")
    print("Done inserting data into DynamoDB.")

if __name__ == "__main__":
    main()
