import boto3
import re
import uuid
import io
from collections import defaultdict, Counter
import matplotlib.pyplot as plt

# Initialisation des clients AWS
dynamodb = boto3.resource("dynamodb", region_name="eu-west-3")
reviews_table = dynamodb.Table("Reviews")
s3_client = boto3.client("s3")

# Nom du bucket S3 pour les graphiques
CHARTS_BUCKET = "foodsentinelle-charts-2025"

SENTIMENT_MAP = {
    "POSITIVE": 1.0,
    "NEGATIVE": -1.0,
    "NEUTRAL": 0.0
}

def nettoyer_texte(texte):
    texte = texte.lower()
    texte = re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿñæœ\s]", " ", texte)
    return texte.strip()

def lire_data_reviews():
    response = reviews_table.scan()
    items = response.get("Items", [])
    return items

def construire_nuage_points_mots(items):
    word_freq = Counter()
    word_sent_sum = defaultdict(float)
    word_sent_count = Counter()

    for it in items:
        text = it.get("text", "")
        sentiment_label = it.get("sentiment")
        if not text or not sentiment_label:
            continue
        score = SENTIMENT_MAP.get(sentiment_label, 0.0)

        txt_clean = nettoyer_texte(text)
        words = txt_clean.split()
        for w in words:
            word_freq[w] += 1
            word_sent_sum[w] += score
            word_sent_count[w] += 1

    X = []
    Y = []
    labels = []
    for w, freq in word_freq.items():
        if freq < 2:
            continue
        nb_sent = word_sent_count[w]
        if nb_sent == 0:
            continue
        avg_sent = word_sent_sum[w] / nb_sent
        X.append(freq)
        Y.append(avg_sent)
        labels.append(w)

    if not X:
        print("Aucun mot à représenter dans le nuage de points.")
        return None

    plt.figure(figsize=(10,6))
    plt.scatter(X, Y, alpha=0.7)
    plt.title("Nuage de points : fréquence vs sentiment moyen des mots")
    plt.xlabel("Fréquence du mot (nb d'occurrences)")
    plt.ylabel("Sentiment moyen (-1 = négatif, +1 = positif)")
    plt.grid(True)

    data_sorted = sorted(zip(X, Y, labels), key=lambda e: e[0], reverse=True)
    for i, (xv, yv, w) in enumerate(data_sorted[:10]):
        plt.annotate(w, (xv, yv), fontsize=9)

    plt.tight_layout()
    
    # Générer un nom de fichier avec UUID et préfixe "charts/"
    scatter_key = f"charts/nuage_points_freq_sent_{uuid.uuid4()}.png"
    
    # Sauvegarder le graphique dans un buffer en mémoire
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    # Upload sur S3
    s3_client.put_object(
        Bucket=CHARTS_BUCKET,
        Key=scatter_key,
        Body=buffer.getvalue(),
        ContentType="image/png"
    )
    plt.close()
    return scatter_key

def construire_histogramme_sentiments(items):
    sentiments = []
    for it in items:
        s = it.get("sentiment")
        if s in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
            sentiments.append(s)
    if not sentiments:
        print("Aucun sentiment trouvé, histogramme impossible.")
        return None

    c = Counter(sentiments)
    labels = list(c.keys())
    values = list(c.values())

    plt.figure(figsize=(6,4))
    color_map = {"POSITIVE": "green", "NEGATIVE": "red", "NEUTRAL": "gray"}
    colors = [color_map.get(l, "blue") for l in labels]
    plt.bar(labels, values, color=colors)
    plt.title("Répartition des sentiments")
    plt.xlabel("Sentiment")
    plt.ylabel("Nombre d'avis")
    plt.tight_layout()
    
    # Générer un nom de fichier avec UUID et préfixe "charts/"
    histo_key = f"charts/sentiment_hist_{uuid.uuid4()}.png"
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    # Upload sur S3
    s3_client.put_object(
        Bucket=CHARTS_BUCKET,
        Key=histo_key,
        Body=buffer.getvalue(),
        ContentType="image/png"
    )
    plt.close()
    return histo_key

def handler(event, context):
    items = lire_data_reviews()
    print(f"{len(items)} avis récupérés depuis la table Reviews.")

    scatter_key = construire_nuage_points_mots(items)
    if scatter_key:
        print(f"[OK] Nuage de points généré et uploadé sur S3 sous la clé : {scatter_key}")

    histo_key = construire_histogramme_sentiments(items)
    if histo_key:
        print(f"[OK] Histogramme généré et uploadé sur S3 sous la clé : {histo_key}")

    print("Terminé.")
    return {
        "statusCode": 200,
        "body": "Graphiques générés et uploadés sur S3."
    }

if __name__ == "__main__":
    handler({}, None)
