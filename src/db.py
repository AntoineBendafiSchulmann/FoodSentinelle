import boto3

dynamodb = boto3.resource("dynamodb", region_name="eu-west-3")

restaurants_table = dynamodb.Table("Restaurants")
reviews_table = dynamodb.Table("Reviews")

def put_restaurant(restaurant_id, name, address, rating, yelp_id):
    item = {
        "restaurant_id": restaurant_id,
        "name": name,
        "address": address,
        "rating": rating,
        "yelp_id": yelp_id
    }
    restaurants_table.put_item(Item=item)

def put_review(review_id, restaurant_id, text, rating, time_created):
    item = {
        "review_id": review_id,
        "restaurant_id": restaurant_id,
        "text": text,
        "rating": rating,
        "time_created": time_created
    }
    reviews_table.put_item(Item=item)
