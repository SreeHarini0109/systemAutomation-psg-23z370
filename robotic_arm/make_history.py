import csv
import random
from pathlib import Path

random.seed(7)

# normal torque range per joint (Nm)
NORMAL_TORQUE = {"shoulder": (80, 120), "elbow": (40, 70), "wrist": (10, 25)}


def make_row(joint):
    wear = random.random()  # 0 = new joint, 1 = about to fail
    low, high = NORMAL_TORQUE[joint]

    torque = random.uniform(low, high) * (1 + 0.35 * wear)  # worn gears need more torque
    temp = random.uniform(35, 50) + 30 * wear
    vibration = random.uniform(1.0, 3.0) + 7 * wear
    run_hours = int(500 + 9000 * wear + random.uniform(-800, 800))

    worn = 1 if wear > 0.6 else 0
    if random.random() < 0.05:  # a few mislabeled records, like real logs
        worn = 1 - worn

    return [joint, round(torque, 1), round(temp, 1), round(vibration, 2), max(run_hours, 0), worn]


out = Path(__file__).parent / "joint_history.csv"
with out.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["joint", "torque_nm", "temp_c", "vibration_mm_s", "run_hours", "worn"])
    for _ in range(40):
        for joint in NORMAL_TORQUE:
            writer.writerow(make_row(joint))

print(f"wrote 120 rows to {out}")
