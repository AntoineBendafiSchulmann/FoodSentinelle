# FoodSentielle

FoodSentinelle is a project designed to manipulate and analyze restaurant reviews based on city names, leveraging AWS services, sentiment analysis, and automation.

---

## **Table of Contents**

- [Project Overview](#project-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Lambda Behavior](#lambda-behavior)
- [Dashboard Quicksight](#dashboard-quicksight)
- [Contributors](#contributors)

---

## **Project Overview**

This project integrates multiple technologies and services, including:

- **AWS Amplify** – For front-end hosting and backend integration.
- **Yelp Fusion API** – To fetch restaurant data and reviews.
- **DynamoDB** – For storing restaurant reviews and metadata.
- **VaderSentiment** – For sentiment analysis of customer reviews.
- **Flask** – As a lightweight API to process data.
- **Selenium** – For web scraping automation.
- **AWS Lambda** – For scheduled automation of data retrieval.
- **Dashboard Quicksight** – For data visualization and analytics.
- **Bucket S3** – For storing processed data and assets.
- **AWS IAM** – For managing permissions and security.

---

## **Prerequisites**

Before you begin, ensure you have the following installed:

- **Git** – For handling repositories.
- **Python** – For setting up a virtual environment and dependencies.

---

## **Installation**

### 1. **Clone the FoodSentinelle repository**

First, clone this repository:

```bash
git clone <foodsentinelle-repository-url>
cd foodsentinelle
```

### 2. **Set up your environment variables**

Copy the environment variable template:

```bash
cp .env.example .env
```

Then, update the `.env` file with the required API keys and credentials.

### 3. **Set up your Python environment**

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

> **Note:** Ensure you see `(venv)` in your terminal before proceeding.

Install the required dependencies:

```bash
pip install -r requirements.txt
```

---

## **Usage**

To fetch restaurant reviews for a specific city, use the following command:

```bash
python -m src.main <city>
```

This will retrieve details of 10 restaurants and pick 10 random reviews.

---

## **Lambda Behavior**

A scheduled AWS Lambda function runs every **XX hours** to fetch and update restaurant ratings and reviews automatically.

---

## **Dashboard Quicksight**

Amazon QuickSight is integrated to provide interactive visual analytics on the collected restaurant data. The dashboard includes:

- **Sentiment Analysis Trends** – Displays positive, neutral, and negative review trends.
- **Top-Rated Restaurants** – Highlights the highest-rated places per city.
- **Customer Review Insights** – Shows common keywords and sentiment distribution.
- **Time-Based Metrics** – Tracks restaurant ratings over time.

To access the QuickSight dashboard, log in to your AWS QuickSight account and navigate to the **FoodSentinelle Dashboard**.

---

### FoodSentinelle API Documentation
1. **GET /restaurants**  
   - Renvoie la liste de restaurants stockés dans la table DynamoDB `Restaurants`.

2. **GET /visuals?file=...**  
   - Retourne un lien (valable 1 heure) pour télécharger le nuage de points depuis un bucket S3.


Pour invoquer la Lambda en local (via AWS CLI) et enregistrer la réponse dans un fichier (par exemple out.json):

```bash
aws lambda invoke \
  --function-name FoodSentinelleAPI \
  --cli-binary-format raw-in-base64-out \
  --payload '{"path":"/restaurants","httpMethod":"GET"}' \
  restaurants.json

cat restaurants.json
```

De même, pour tester le second endpoint , par contre le lien périme après 1 heure:

```bash
aws lambda invoke \
  --function-name FoodSentinelleAPI \
  --cli-binary-format raw-in-base64-out \
  --payload '{"path":"/visuals","httpMethod":"GET","queryStringParameters":{"file":"nuage_points_freq_sent"}}' \
    visuals.json

```
ca donnera un fichier visuals.json contenant le lien pour télécharger le nuage de points.

de cette forme :

```json
{
{"statusCode": 200, "body": "{\"url\": \"LIEN-A-COLLER-DANS-UN-NAVIGATEUR\"}", "headers": {"Content-Type": "application/json"}}
}
```

## **Contributors**

Antoine Bendafi-Schulmann
Sorën Messelier-Sentis