import boto3
import re
import matplotlib.pyplot as plt
import uuid
from collections import defaultdict, Counter

dynamodb = boto3.resource("dynamodb", region_name="eu-west-3")
reviews_table = dynamodb.Table("Reviews")

SENTIMENT_MAP = {
    "POSITIVE": 1.0,
    "NEGATIVE": -1.0,
    "NEUTRAL": 0.0
}

SCATTER_FILE = f"charts/nuage_points_freq_sent_{uuid.uuid4()}.png"
HISTO_FILE = f"charts/sentiment_hist_{uuid.uuid4()}.png"

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
    plt.savefig(SCATTER_FILE)
    plt.close()
    return SCATTER_FILE

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
    plt.savefig(HISTO_FILE)
    plt.close()
    return HISTO_FILE

def main():
    items = lire_data_reviews()
    print(f"{len(items)} avis récupérés depuis la table Reviews.")

    scatter_file = construire_nuage_points_mots(items)
    if scatter_file:
        print(f"[OK] Nuage de points généré : {scatter_file}")

    histo_file = construire_histogramme_sentiments(items)
    if histo_file:
        print(f"[OK] Histogramme généré : {histo_file}")

    print("Terminé.")

if __name__ == "__main__":
    main()
