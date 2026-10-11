import csv
import random
from pathlib import Path


def generate_state(temp, pressure, vib, rpm, current):
    if temp > 90 or pressure > 170 or vib > 2.5 or rpm > 2850 or current > 20:
        return "CRITICAL"
    if temp > 80 or pressure > 150 or vib > 1.5 or rpm > 2300 or current > 15:
        return "WARNING"
    return "NORMAL"


def generate_sensor_history(rows=250):
    csv_path = Path(__file__).resolve().parent / "sensor_history.csv"

    with csv_path.open("w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["temp", "pressure", "vib", "rpm", "current", "state"])

        for _ in range(rows):
            temp = round(random.uniform(60, 98), 2)
            pressure = round(random.uniform(110, 185), 2)
            vib = round(random.uniform(0.2, 3.2), 3)
            rpm = random.randint(900, 3200)
            current = round(random.uniform(6.0, 24.0), 2)
            state = generate_state(temp, pressure, vib, rpm, current)
            writer.writerow([temp, pressure, vib, rpm, current, state])

    return csv_path


if __name__ == "__main__":
    output_file = generate_sensor_history()
    print(f"Sensor history generated at: {output_file}")
    