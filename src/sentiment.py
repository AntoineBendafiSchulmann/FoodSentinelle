import boto3
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

dynamodb = boto3.resource("dynamodb", region_name="eu-west-3")
reviews_table = dynamodb.Table("Reviews")

analyzer = SentimentIntensityAnalyzer()

def compute_sentiment_vader(text):
    scores = analyzer.polarity_scores(text)
    compound = scores["compound"]
    if compound > 0.05:
        return "POSITIVE"
    elif compound < -0.05:
        return "NEGATIVE"
    else:
        return "NEUTRAL"

def main():
    response = reviews_table.scan()
    items = response.get("Items", [])
    print(f"Found {len(items)} reviews to process.")

    count = 0
    for item in items:
        review_id = item["review_id"]
        text = item.get("text", "")
        sentiment = compute_sentiment_vader(text)

        reviews_table.update_item(
            Key={"review_id": review_id},
            UpdateExpression="SET sentiment = :s",
            ExpressionAttributeValues={":s": sentiment}
        )
        count += 1

    print(f"Sentiment updated for {count} reviews.")

if __name__ == "__main__":
    main()
