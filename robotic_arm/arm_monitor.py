import re
import sys
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier

HERE = Path(__file__).parent

# hard limits, anything above these stops the arm right away
DANGER = {
    "torque_nm": {"shoulder": 180, "elbow": 110, "wrist": 40},
    "temp_c": 85,
    "vibration_mm_s": 12,
}

# motor torque constant (Nm per amp), used to check the torque sensor
KT = {"shoulder": 8.0, "elbow": 5.0, "wrist": 1.6}
SPOOF_TOLERANCE = 0.25

SEVERE_WORDS = ["grinding", "burning", "smoke", "sparks", "cracked", "seized"]
MILD_WORDS = ["squeak", "noise", "rough", "backlash", "play", "hot", "rattle", "loose", "leak"]

# latest snapshot from the fleet: torque, motor current, temp, vibration, run hours
FLEET = {
    "ARM-01": {
        "shoulder": (95, 11.9, 42, 1.8, 1200),
        "elbow": (52, 10.4, 40, 1.6, 1100),
        "wrist": (15, 9.4, 38, 1.5, 1300),
    },
    "ARM-02": {
        "shoulder": (100, 12.5, 44, 2.0, 2600),
        "elbow": (55, 11.0, 43, 2.1, 2500),
        "wrist": (18, 11.2, 48, 2.9, 3000),
    },
    "ARM-03": {
        "shoulder": (110, 13.8, 48, 2.6, 4100),
        "elbow": (82, 16.4, 72, 8.5, 8600),
        "wrist": (20, 12.5, 45, 2.4, 3900),
    },
    "ARM-04": {
        "shoulder": (98, 12.2, 45, 2.0, 2200),
        "elbow": (50, 10.0, 44, 1.9, 2100),
        "wrist": (22, 13.8, 91, 3.1, 2400),
    },
    "ARM-05": {
        "shoulder": (105, 24.0, 58, 4.0, 5000),  # torque says 105 but the motor is pulling 24 A
        "elbow": (60, 12.0, 46, 2.2, 3000),
        "wrist": (17, 10.6, 41, 1.8, 2900),
    },
}


def check_spoof(joint, torque, current):
    expected = current * KT[joint]
    if abs(torque - expected) > SPOOF_TOLERANCE * expected:
        return expected
    return None


def safety_check(joint, torque, temp, vibration):
    hits = []
    if torque > DANGER["torque_nm"][joint]:
        hits.append(f"{joint} torque {torque:.0f} Nm")
    if temp > DANGER["temp_c"]:
        hits.append(f"{joint} temp {temp} C")
    if vibration > DANGER["vibration_mm_s"]:
        hits.append(f"{joint} vibration {vibration} mm/s")
    return hits


def to_features(df):
    return pd.get_dummies(df, columns=["joint"]).reindex(
        columns=["torque_nm", "temp_c", "vibration_mm_s", "run_hours",
                 "joint_shoulder", "joint_elbow", "joint_wrist"],
        fill_value=0,
    )


def train_model():
    history = pd.read_csv(HERE / "joint_history.csv")
    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(to_features(history.drop(columns="worn")), history["worn"])
    return model


def wear_probability(model, joint, torque, temp, vibration, hours):
    row = pd.DataFrame([{"joint": joint, "torque_nm": torque, "temp_c": temp,
                         "vibration_mm_s": vibration, "run_hours": hours}])
    return model.predict_proba(to_features(row))[0][1]


def read_notes():
    notes = {}
    for line in (HERE / "maintenance_log.txt").read_text().splitlines():
        arm = re.search(r"ARM-\d+", line)
        if not arm:
            continue  # not about an arm, skip it
        words = re.findall(r"[a-z]+", line.lower())
        score = 0
        for i, word in enumerate(words):
            if i > 0 and words[i - 1] in ("no", "not", "without"):
                continue
            # startswith so "squeaking" and "noises" still count
            if any(word.startswith(k) for k in SEVERE_WORDS):
                score += 3
            elif any(word.startswith(k) for k in MILD_WORDS):
                score += 1
        notes[arm.group()] = notes.get(arm.group(), 0) + score
    return notes


def decide(danger, spoofed, wear, note_score):
    if danger:
        return "EMERGENCY_STOP"
    if spoofed or note_score >= 3 or (wear is not None and wear >= 0.7):
        return "SCHEDULE_MAINTENANCE"
    if note_score >= 1 and wear is not None and wear >= 0.4:
        return "SCHEDULE_MAINTENANCE"  # both signals agree, don't wait
    if note_score >= 1 or (wear is not None and wear >= 0.4):
        return "MONITOR"
    return "SAFE"


def main():
    model = None
    if "--no-model" not in sys.argv:
        try:
            model = train_model()
        except Exception as e:
            print(f"model unavailable ({e}), running on rules and notes only")

    notes = read_notes()

    for arm, joints in FLEET.items():
        danger, spoofed, wear = [], [], None

        for joint, (torque, current, temp, vibration, hours) in joints.items():
            if None in (torque, current, temp, vibration):
                danger.append(f"{joint} reading missing, can't confirm it's safe")
                continue

            real_torque = check_spoof(joint, torque, current)
            if real_torque is not None:
                spoofed.append(f"{joint} reports {torque} Nm, current says {real_torque:.0f} Nm")
                torque = max(torque, real_torque)
            danger += safety_check(joint, torque, temp, vibration)

            if model is not None:
                try:
                    p = wear_probability(model, joint, torque, temp, vibration, hours)
                    wear = p if wear is None else max(wear, p)
                except Exception as e:
                    print(f"model failed on {arm} {joint} ({e}), skipping wear check")

        decision = decide(danger, spoofed, wear, notes.get(arm, 0))

        print(f"\n{arm}: {decision}")
        print(f"  wear risk : {'n/a' if wear is None else f'{wear:.2f}'}")
        print(f"  note score: {notes.get(arm, 0)}")
        for s in spoofed:
            print(f"  SPOOF     : {s}")
        for d in danger:
            print(f"  DANGER    : {d}")


if __name__ == "__main__":
    main()
