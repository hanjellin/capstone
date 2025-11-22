import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

# 데이터 로드
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "snapshot_dataset.csv")
df = pd.read_csv(DATA_PATH)

# 입력 피처(X) / 출력 라벨(y)
FEATURES = [
    "cpu_usage", "cpu_temp",
    "gpu_temp", "gpu_usage", "gpu_mem",
    "disk_temp", "disk_life", "disk_spare"
]

TARGET = "risk_class"

X = df[FEATURES]
y = df[TARGET]

# Train/val 분리
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

# RandomForest 모델
model = RandomForestClassifier(
    n_estimators=300,
    max_depth=10,
    random_state=42
)

# 학습
model.fit(X_train, y_train)
acc = model.score(X_val, y_val)

print(f"Validation Accuracy: {acc*100:.2f}%")

# 모델 저장
MODEL_PATH = os.path.join(os.path.dirname(__file__), "snapshot_model.pkl")
joblib.dump(model, MODEL_PATH)

print("Model saved:", MODEL_PATH)
