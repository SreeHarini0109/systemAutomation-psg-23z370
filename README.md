# systemAutomation-psg-23z370

Work for the 23IF02 System Automation course.

## Folders

| Folder | What's in it |
|---|---|
| `day1/` | Rule engine that monitors five factory machines and picks the one that needs attention first |
| `day2/` | Rule engine combined with a RandomForest model trained on sensor history |
| `robotic_arm/` | Assignment: joint health monitoring for a fleet of 6-axis robotic arms |

## Setup

```bash
pip install -r requirements.txt
```

## Robotic Arm Joint Health Monitoring

Each arm reports torque, motor current, temperature and vibration for its shoulder, elbow and wrist joints. The system gives every arm one decision: `SAFE`, `MONITOR`, `SCHEDULE_MAINTENANCE` or `EMERGENCY_STOP`.

### Files

- `make_history.py` creates `joint_history.csv`, 120 labeled readings from past joints (`worn` = 1 means the joint was close to failing)
- `maintenance_log.txt` holds technician notes in plain sentences, some about the arms and some not
- `arm_monitor.py` runs the full pipeline

### Run

```bash
cd robotic_arm
python3 make_history.py
python3 arm_monitor.py
python3 arm_monitor.py --no-model   # same run with the ML model turned off
```

### How it works

1. **Spoof check:** torque should match motor current × torque constant. If they differ by more than 25%, the torque sensor is flagged and the higher value is used.
2. **Safety stop:** fixed limits, no model involved. Torque above 180 / 110 / 40 Nm (shoulder / elbow / wrist), temperature above 85 °C, or vibration above 12 mm/s.
3. **Wear prediction:** a RandomForest trained on `joint_history.csv` gives each joint a wear risk, and the arm takes the highest.
4. **Maintenance notes:** only notes that name an arm count. Severe words (grinding, burning, smoke...) add 3, mild words (squeak, backlash, hot...) add 1. A word after "no", "not" or "without" is skipped, and words are matched by how they start, so "squeaking" counts as "squeak".

### Decision rules

| Decision | When |
|---|---|
| `EMERGENCY_STOP` | Any safety limit crossed, or a sensor reading is missing |
| `SCHEDULE_MAINTENANCE` | Spoof found, note score 3+, wear risk 0.7+, or a mild note together with wear risk 0.4+ |
| `MONITOR` | Any mild note, or wear risk 0.4+ |
| `SAFE` | None of the above |

### Sample output

| Arm | Decision | Why |
|---|---|---|
| ARM-01 | SAFE | Low wear risk; note says "no noise" |
| ARM-02 | MONITOR | Technician heard a squeak in the wrist |
| ARM-03 | SCHEDULE_MAINTENANCE | Wear risk 0.91 and a note about elbow grinding |
| ARM-04 | EMERGENCY_STOP | Wrist at 91 °C |
| ARM-05 | EMERGENCY_STOP | Torque sensor says 105 Nm but current implies 192 Nm, over the shoulder limit |
