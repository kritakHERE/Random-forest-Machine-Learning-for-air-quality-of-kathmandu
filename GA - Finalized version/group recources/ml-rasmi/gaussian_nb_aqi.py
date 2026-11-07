# Gaussian Naive Bayes - AQI category classifier (Rashmi)
# Weather + time features only. Time-based split (train before 2025-10-01, test 2025-10-01 to 2026-09-30).
import pandas as pd
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix

df = pd.read_csv("kathmandu_final.csv")
df["time"] = pd.to_datetime(df["time"])
df = df.sort_values("time").reset_index(drop=True)

# time features
df["hour"] = df.time.dt.hour
df["month"] = df.time.dt.month
df["dayofweek"] = df.time.dt.dayofweek

# AQI category from us_aqi (rare bands merged)
def band(a):
    if a <= 100: return "Good/Moderate"
    if a <= 150: return "Unhealthy for Sensitive (101-150)"
    return "Unhealthy (151+)"   # 151-217 merged: the 201+ band has only ~45 rows
df["label"] = df["us_aqi"].apply(band)

# drop leakage (pollutants + target) and duplicate column (rain == precipitation)
drop = ["time","us_aqi","label","pm10","pm2_5","carbon_monoxide","nitrogen_dioxide",
        "sulphur_dioxide","ozone","aerosol_optical_depth","dust","uv_index","rain"]
X = df.drop(columns=drop)
X = pd.get_dummies(X, columns=["weather_code"], dtype=float)  # weather_code is a category
y = df["label"]

# Time split (team rule): test = last year, Oct 1 2025 to Sep 30 2026; train = everything before
# time split: train = 2022-10-01 to 2025-09-30, test = 2025-10-01 to 2026-09-30
is_train = (df["time"] >= "2022-10-01") & (df["time"] < "2025-10-01")
is_test = df["time"] >= "2025-10-01"
Xtr, Xte, ytr, yte = X[is_train], X[is_test], y[is_train], y[is_test]

print("Train rows:", len(Xtr), "| Test rows:", len(Xte))
print("\nTrain class counts:\n", ytr.value_counts())
print("\nTest class counts:\n", yte.value_counts())

model = GaussianNB().fit(Xtr, ytr)
pred = model.predict(Xte)

print("\nAccuracy:", round(accuracy_score(yte, pred), 4))
print("Macro F1:", round(f1_score(yte, pred, average="macro"), 4))
print("\n", classification_report(yte, pred, zero_division=0))
labels = sorted(y.unique())
print("Labels:", labels)
print(confusion_matrix(yte, pred, labels=labels))
