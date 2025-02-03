import sys
import uuid
from decimal import Decimal

from src.yelp_api import get_restaurants_by_location, get_reviews
from src.db import put_restaurant, put_review

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
        name = r.get("name", "")
        
        address = ""
        if "location" in r and "display_address" in r["location"]:
            address = ", ".join(r["location"]["display_address"])
        
        rating_float = r.get("rating", 0)
        rating = Decimal(str(rating_float))
        
        yelp_id = r["id"]

        put_restaurant(
            restaurant_id=restaurant_id,
            name=name,
            address=address,
            rating=rating,  
            yelp_id=yelp_id
        )
        print(f"[+] Inserted Restaurant: {name} (ID: {restaurant_id})")

        reviews = get_reviews(business_id=restaurant_id)
        print(f"  -> Found {len(reviews)} reviews for {name}.")

        for rev in reviews:
            review_id = str(uuid.uuid4())
            text = rev.get("text", "")
            
            review_rating_float = rev.get("rating", 0)
            review_rating = Decimal(str(review_rating_float))
            
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
