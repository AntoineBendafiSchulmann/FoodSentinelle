import boto3
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Initialisation du client DynamoDB dans la région eu-west-3
dynamodb = boto3.resource("dynamodb", region_name="eu-west-3")
reviews_table = dynamodb.Table("Reviews")

# Initialisation de l'analyseur de sentiment
analyzer = SentimentIntensityAnalyzer()

def compute_sentiment_vader(text):
    """
    Calcule le sentiment d'un texte avec VaderSentiment.
    Retourne "POSITIVE", "NEGATIVE" ou "NEUTRAL".
    """
    scores = analyzer.polarity_scores(text)
    compound = scores["compound"]
    if compound > 0.05:
        return "POSITIVE"
    elif compound < -0.05:
        return "NEGATIVE"
    else:
        return "NEUTRAL"

def handler(event, context):
    """
    Handler principal de la Lambda.
    - Récupère tous les items de la table Reviews.
    - Calcule le sentiment pour chaque review.
    - Met à jour l'item avec le sentiment.
    """
    # Récupération des items via un scan
    response = reviews_table.scan()
    items = response.get("Items", [])
    print(f"Found {len(items)} reviews to process.")
    
    count = 0
    for item in items:
        review_id = item["review_id"]
        text = item.get("text", "")
        sentiment = compute_sentiment_vader(text)
        
        # Mise à jour de l'item avec le sentiment
        reviews_table.update_item(
            Key={"review_id": review_id},
            UpdateExpression="SET sentiment = :s",
            ExpressionAttributeValues={":s": sentiment}
        )
        count += 1
    
    print(f"Sentiment updated for {count} reviews.")
    
    return {
        "statusCode": 200,
        "body": f"Sentiment updated for {count} reviews."
    }
