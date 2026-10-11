import random
import time
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split


LOG_FILE = Path(__file__).resolve().parent / "combined_pipeline_log.txt"
DATASET_PATH = Path(__file__).resolve().parent / "data" / "day2_sample.csv"


RULES = [
    {
        "name": "CRITICAL_TEMP",
        "priority": 1,
        "condition": lambda r: r.get("temperature") is not None and r["temperature"] > 90,
        "action": "STOP_MACHINE",
    },
    {
        "name": "CRITICAL_PRESSURE",
        "priority": 2,
        "condition": lambda r: r.get("pressure") is not None and r["pressure"] > 140,
        "action": "EMERGENCY_SHUTDOWN",
    },
    {
        "name": "HIGH_TEMP",
        "priority": 3,
        "condition": lambda r: r.get("temperature") is not None and r["temperature"] > 80,
        "action": "REDUCE_SPEED",
    },
    {
        "name": "HIGH_PRESSURE",
        "priority": 4,
        "condition": lambda r: r.get("pressure") is not None and r["pressure"] > 120,
        "action": "ALERT_OPERATOR",
    },
    {
        "name": "HIGH_VIBRATION",
        "priority": 5,
        "condition": lambda r: r.get("vibration") is not None and r["vibration"] > 4.5,
        "action": "INSPECT_MOTOR",
    },
    {
        "name": "HIGH_CURRENT",
        "priority": 6,
        "condition": lambda r: r.get("current") is not None and r["current"] > 18,
        "action": "CHECK_LOAD",
    },
    {
        "name": "LOW_TEMP",
        "priority": 7,
        "condition": lambda r: r.get("temperature") is not None and r["temperature"] < 55,
        "action": "WARN_HEATER",
    },
]


def generate_sensor_data():
    temperature = random.uniform(50, 95)
    pressure = random.uniform(80, 130)
    vibration = random.uniform(0.2, 5.8)
    current = random.uniform(5, 22)
    rpm = random.randint(900, 3200)

    if random.random() < 0.10:
        temperature = None
    if random.random() < 0.08:
        pressure = random.uniform(135, 170)
    if random.random() < 0.09:
        current = None

    return {
        "temperature": round(temperature, 1) if temperature is not None else None,
        "pressure": round(pressure, 1),
        "vibration": round(vibration, 2),
        "current": round(current, 2) if current is not None else None,
        "rpm": rpm,
    }


def evaluate_rules(reading, rules):
    ordered = sorted(rules, key=lambda rule: rule.get("priority", 999))
    for rule in ordered:
        condition = rule.get("condition")
        if callable(condition) and condition(reading):
            return rule.get("name", "UNKNOWN_RULE"), rule.get("action", "CONTINUE_NORMAL")
    return "NO_RULE_FIRED", "CONTINUE_NORMAL"


def rule_to_state(rule_name):
    mapping = {
        "CRITICAL_TEMP": "OVERHEATING",
        "HIGH_TEMP": "OVERHEATING",
        "HIGH_VIBRATION": "HIGH_VIBRATION",
        "HIGH_CURRENT": "MOTOR_OVERLOAD",
        "CRITICAL_PRESSURE": "LOW_PRESSURE",
        "HIGH_PRESSURE": "LOW_PRESSURE",
        "LOW_TEMP": "NORMAL",
        "NO_RULE_FIRED": "NORMAL",
    }
    return mapping.get(rule_name, "NORMAL")


def take_action(action):
    actions = {
        "STOP_MACHINE": "Emergency stop: machine halted for inspection.",
        "EMERGENCY_SHUTDOWN": "Emergency shutdown: isolate machine and inspect immediate hazards.",
        "REDUCE_SPEED": "Reduce machine speed and monitor readings closely.",
        "ALERT_OPERATOR": "Alert operator: pressure is above safe threshold.",
        "INSPECT_MOTOR": "Inspect motor and bearings for excessive vibration.",
        "CHECK_LOAD": "Check the load on the motor and electrical supply.",
        "WARN_HEATER": "Warning: temperature is below expected operating range.",
        "CONTINUE_NORMAL": "Continue normal operation.",
    }
    return actions.get(action, f"(no handler yet for action: {action})")


def load_training_data():
    df = pd.read_csv(DATASET_PATH)
    feature_cols = ["temperature", "pressure", "vibration", "current", "rpm"]
    target_col = "state"

    X = df[feature_cols]
    y = df[target_col].astype(str)
    return X, y


def train_ai_model():
    X, y = load_training_data()
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

    print(f"AI accuracy: {accuracy:.4f}")
    print(f"AI weighted F1: {f1:.4f}")
    return model


def predict_ai_state(model, reading):
    row = {
        "temperature": reading.get("temperature"),
        "pressure": reading.get("pressure"),
        "vibration": reading.get("vibration"),
        "current": reading.get("current"),
        "rpm": reading.get("rpm"),
    }
    return model.predict(pd.DataFrame([row]))[0]


def log_decision(machine_id, reading, rule_name, rule_state, ai_state_before, ai_state_after, action):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as log_file:
        log_file.write(
            f"{timestamp} | machine={machine_id} | reading={reading} | "
            f"rule_name={rule_name} | rule_state={rule_state} | "
            f"ai_state_before={ai_state_before} | ai_state_after={ai_state_after} | "
            f"action={action}\n"
        )


def main():
    LOG_FILE.write_text("", encoding="utf-8")
    model = train_ai_model()

    machine_id = "M1"
    reading = generate_sensor_data()
    rule_name, action = evaluate_rules(reading, RULES)
    rule_state = rule_to_state(rule_name)
    ai_state_before = predict_ai_state(model, reading)
    ai_state_after = rule_state if ai_state_before != rule_state else ai_state_before

    print("=== SINGLE MACHINE FINAL PIPELINE ===")
    print(f"Machine ID: {machine_id}")
    print(f"Sensor reading: {reading}")
    print(f"Rule name: {rule_name}")
    print(f"Rule state: {rule_state}")
    print(f"AI state before fix: {ai_state_before}")
    print(f"AI state after fix: {ai_state_after}")
    print(f"Action: {take_action(action)}")

    log_decision(machine_id, reading, rule_name, rule_state, ai_state_before, ai_state_after, action)
    print(f"\nLog saved to: {LOG_FILE}")


if __name__ == "__main__":
    main()
