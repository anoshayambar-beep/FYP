# ml_training.py
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)
import seaborn as sns
import matplotlib.pyplot as plt
import joblib

# 1. Load dataset
data = pd.read_csv("dataset.csv")  # Replace with your dataset path
print("Dataset loaded successfully")
print("Dataset shape:", data.shape)

# 2. Automatically detect target column (assuming it's the last column)
target_col = data.columns[-1]
print("Target column detected as:", target_col)

# 3. Separate features and target
X = data.drop(target_col, axis=1)
y = data[target_col]

# 4. Encode categorical features and remember encoders for API use
categorical_cols = X.select_dtypes(include=["object"]).columns.tolist()
feature_encoders = {}

for col in categorical_cols:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col].astype(str))
    feature_encoders[col] = le

# Encode target if categorical and remember encoder
target_encoder = None
if y.dtype == "object":
    target_encoder = LabelEncoder()
    y = target_encoder.fit_transform(y.astype(str))
    class_names = target_encoder.classes_
else:
    class_names = [str(cls) for cls in sorted(y.unique())]

print("Categorical features encoded. New shape:", X.shape)

# 5. Split into train and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 6. Train Random Forest classifier
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
print("Model training completed")

# 7. Make predictions
y_pred = model.predict(X_test)

# 8. Evaluate model

# 8a. Weighted metrics (overall)
print("\n--- Overall Metrics (Weighted) ---")
print("Accuracy :", accuracy_score(y_test, y_pred))
print("Precision:", precision_score(y_test, y_pred, average='weighted'))
print("Recall   :", recall_score(y_test, y_pred, average='weighted'))
print("F1 Score :", f1_score(y_test, y_pred, average='weighted'))

# 8b. Per-class metrics
print("\n--- Per-Class Metrics ---")
print(classification_report(y_test, y_pred, target_names=class_names))

# 8c. Confusion matrix
cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(10,7))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=class_names, yticklabels=class_names)
plt.xlabel('Predicted')
plt.ylabel('Actual')
plt.title('Confusion Matrix')
plt.show()

# 9. Save model and preprocessing artifacts together for API usage
artifacts = {
    "model": model,
    "feature_columns": X.columns.tolist(),
    "categorical_columns": categorical_cols,
    "feature_encoders": feature_encoders,
    "target_encoder": target_encoder,
    "class_names": class_names,
}

joblib.dump(artifacts, "ransomware_model.pkl")
print("Model and artifacts saved as ransomware_model.pkl")

