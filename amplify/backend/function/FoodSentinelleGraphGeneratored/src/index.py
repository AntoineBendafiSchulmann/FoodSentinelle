import boto3
import re
import uuid
import io
from collections import defaultdict, Counter

import pygal
from pygal.style import DefaultStyle

# Initialisation des clients AWS
dynamodb = boto3.resource("dynamodb", region_name="eu-west-3")
reviews_table = dynamodb.Table("Reviews")
s3_client = boto3.client("s3")

CHARTS_BUCKET = "foodsentinelle-charts-2025"

SENTIMENT_MAP = {
    "POSITIVE": 1.0,
    "NEGATIVE": -1.0,
    "NEUTRAL": 0.0
}

def nettoyer_texte(texte):
    texte = texte.lower()
    # Retirer les caractères spéciaux
    texte = re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿñæœ\s]", " ", texte)
    return texte.strip()

def lire_data_reviews():
    response = reviews_table.scan()
    return response.get("Items", [])

def construire_nuage_points_mots(items):
    """
    Construit un nuage de points (SVG) : fréquence d'apparition des mots (X)
    vs sentiment moyen (Y). Les fichiers sont ensuite chargés sur S3.
    """
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

    # Préparation des données
    xy_values = []
    labels = []

    for w, freq in word_freq.items():
        if freq < 2:
            continue
        nb_sent = word_sent_count[w]
        if nb_sent == 0:
            continue
        avg_sent = word_sent_sum[w] / nb_sent
        xy_values.append((freq, avg_sent))
        labels.append(w)

    if not xy_values:
        print("Aucun mot à représenter dans le nuage de points.")
        return None

    # Création d'un graphique XY avec Pygal
    xy_chart = pygal.XY(
        stroke=False,  # Pas de ligne reliant les points
        title="Nuage de points : fréquence vs sentiment moyen",
        x_title="Fréquence (nb occurrences)",
        y_title="Sentiment moyen (-1=négatif, +1=positif)",
        style=DefaultStyle
    )

    # On ajoute une seule série de points
    points = []
    for i, (x, y) in enumerate(xy_values):
        points.append({
            'value': (x, y),
            'label': labels[i]
        })
    xy_chart.add("Mots", points)

    # Rendu en SVG (objet bytes)
    svg_data = xy_chart.render()

    scatter_key = f"charts/nuage_points_freq_sent_{uuid.uuid4()}.svg"

    # Upload sur S3 (pas besoin de .encode(), svg_data est déjà en bytes)
    s3_client.put_object(
        Bucket=CHARTS_BUCKET,
        Key=scatter_key,
        Body=svg_data,
        ContentType="image/svg+xml"
    )

    return scatter_key

def construire_histogramme_sentiments(items):
    """
    Construit un histogramme (SVG) montrant la répartition des sentiments.
    """
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

    # Création d'un graphique à barres
    bar_chart = pygal.Bar(
        title="Répartition des sentiments",
        x_title="Sentiment",
        y_title="Nombre d'avis",
        style=DefaultStyle
    )
    bar_chart.x_labels = labels
    bar_chart.add("Sentiments", values)

    svg_data = bar_chart.render()
    histo_key = f"charts/sentiment_hist_{uuid.uuid4()}.svg"

    s3_client.put_object(
        Bucket=CHARTS_BUCKET,
        Key=histo_key,
        Body=svg_data,  # Déjà en bytes
        ContentType="image/svg+xml"
    )

    return histo_key

def handler(event, context):
    """
    Fonction Lambda qui :
    1. Récupère tous les reviews depuis DynamoDB.
    2. Construit un nuage de points (SVG) : fréquence vs sentiment moyen.
    3. Construit un histogramme (SVG) : répartition des sentiments.
    4. Upload des fichiers SVG vers S3.
    """
    items = lire_data_reviews()
    print(f"{len(items)} avis récupérés depuis la table Reviews.")

    scatter_key = construire_nuage_points_mots(items)
    if scatter_key:
        print(f"[OK] Nuage de points généré et uploadé sur S3 : {scatter_key}")

    histo_key = construire_histogramme_sentiments(items)
    if histo_key:
        print(f"[OK] Histogramme généré et uploadé sur S3 : {histo_key}")

    print("Terminé.")
    return {
        "statusCode": 200,
        "body": "Graphiques (SVG) générés et uploadés sur S3."
    }

if __name__ == "__main__":
    handler({}, None)
