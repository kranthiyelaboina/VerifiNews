"""
Retrain the news classifier model using the LIAR dataset.
Outputs: model/news_classifier.sav
"""

import os
import pickle
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load datasets
train_df = pd.read_csv(os.path.join(BASE_DIR, "data", "train.csv")).dropna()
test_df  = pd.read_csv(os.path.join(BASE_DIR, "data", "test.csv")).dropna()

print(f"Training samples: {len(train_df)}")
print(f"Test samples: {len(test_df)}")

# Build pipeline: TF-IDF + Logistic Regression
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(
        stop_words="english",
        max_df=0.7,
        ngram_range=(1, 2),
    )),
    ("clf", LogisticRegression(
        max_iter=300,
        C=1.0,
        solver="liblinear",
    )),
])

# Train
print("Training...")
pipeline.fit(train_df["Statement"], train_df["Label"])
print("Training complete.")

# Evaluate
preds = pipeline.predict(test_df["Statement"])
print(f"Test Accuracy: {accuracy_score(test_df['Label'], preds):.4f}")

# Save model
model_dir = os.path.join(BASE_DIR, "model")
os.makedirs(model_dir, exist_ok=True)
model_path = os.path.join(model_dir, "news_classifier.sav")
with open(model_path, "wb") as f:
    pickle.dump(pipeline, f)

print(f"Model saved to {model_path}")
