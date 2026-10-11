from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    column_map = {
        "temp": "temperature",
        "temperature": "temperature",
        "pressure": "pressure",
        "vib": "vibration",
        "vibration": "vibration",
        "current": "current",
        "rpm": "rpm",
    }

    df = df.rename(columns=column_map)
    return df


def load_dataset(csv_path: Path):
    df = pd.read_csv(csv_path)
    df = normalize_columns(df)

    required_features = ["temperature", "pressure", "vibration", "current", "rpm"]
    missing = [col for col in required_features if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required feature columns: {missing}")

    target_col = "state" if "state" in df.columns else None
    if target_col is None:
        raise ValueError("CSV must contain a 'state' target column.")

    X = df[required_features]
    y = df[target_col].astype(str)
    return X, y


def train_model(X: pd.DataFrame, y: pd.Series):
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced_subsample",
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    f1 = f1_score(y_test, predictions, average="weighted")

    print("\nModel validation summary")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Weighted F1 Score: {f1:.4f}")
    print(classification_report(y_test, predictions, zero_division=0))

    return model


def predict_examples(model, feature_rows):
    df = pd.DataFrame(feature_rows)
    pred = model.predict(df)
    for row, result in zip(feature_rows, pred):
        print(f"Input: {row} -> Predicted state: {result}")


if __name__ == "__main__":
    csv_path = Path(__file__).resolve().parent / "day2_sample.csv"
    X, y = load_dataset(csv_path)
    model = train_model(X, y)

    example_rows = [
        {"temperature": 68.0, "pressure": 5.1, "vibration": 2.8, "current": 11.2, "rpm": 1700},
        {"temperature": 93.0, "pressure": 5.3, "vibration": 1.4, "current": 12.0, "rpm": 1800},
        {"temperature": 60.0, "pressure": 1.8, "vibration": 1.5, "current": 8.2, "rpm": 2100},
        {"temperature": 72.0, "pressure": 4.8, "vibration": 6.4, "current": 9.4, "rpm": 1800},
        {"temperature": 58.0, "pressure": 5.6, "vibration": 2.8, "current": 20.5, "rpm": 1650},
    ]

    print("\nPrediction examples")
    predict_examples(model, example_rows)
