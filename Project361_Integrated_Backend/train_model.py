"""
Train the Heart Rate Anomaly Detection Model.

Algorithm:
    Isolation Forest

The model learns the pattern of normal heart-rate readings
and can later identify readings that are unusual.
"""

import pandas as pd
import joblib

from sklearn.ensemble import IsolationForest


# --------------------------------------------------
# 1. Load training data
# --------------------------------------------------

data = pd.read_csv("training_data.csv")

print("Training data loaded.")
print(data.head())


# --------------------------------------------------
# 2. Select the feature
# --------------------------------------------------

X = data[["heart_rate"]]


# --------------------------------------------------
# 3. Create the ML model
# --------------------------------------------------

model = IsolationForest(
    contamination=0.05,
    random_state=42
)


# --------------------------------------------------
# 4. Train the model
# --------------------------------------------------

model.fit(X)


# --------------------------------------------------
# 5. Save the trained model
# --------------------------------------------------

joblib.dump(model, "heart_rate_model.pkl")


print()
print("Machine Learning model trained successfully!")
print("Model saved as: heart_rate_model.pkl")