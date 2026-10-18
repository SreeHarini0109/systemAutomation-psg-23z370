# Robotic Arm Joint Health Monitoring: Design Explanation

This document explains three design choices in `arm_monitor.py`: the safety thresholds, how the model and the maintenance log combine into one decision, and how the spoofed-sensor defense works.

## 1. Why these safety thresholds

The immediate-stop check uses fixed limits:

| Reading | Shoulder | Elbow | Wrist |
|---|---|---|---|
| Torque | 180 Nm | 110 Nm | 40 Nm |
| Temperature | 85 °C | 85 °C | 85 °C |
| Vibration | 12 mm/s | 12 mm/s | 12 mm/s |

### Torque

Each joint has a different normal range because it carries a different load. The shoulder lifts the whole arm, while the wrist only moves the tool.

| Joint | Normal range | Highest torque from a worn joint in history | Stop limit |
|---|---|---|---|
| Shoulder | 80–120 Nm | about 147 Nm | 180 Nm |
| Elbow | 40–70 Nm | about 93 Nm | 110 Nm |
| Wrist | 10–25 Nm | about 33 Nm | 40 Nm |

Each limit is about 1.5 to 1.6 times the top of the normal range. Each one also sits above the highest torque reached by any worn joint in the historical dataset. Normal wear never trips the stop because wear is the model's job. A reading above the limit means something more than wear is going on, such as a collision, a jammed joint or an overload.

### Temperature: 85 °C

Healthy joints run at 35–50 °C, and the most worn joints in the history reach about 77 °C. Above 85 °C, gearbox grease starts breaking down quickly, and the motor and encoder electronics get close to their limits. The value is also above the worst case from wear alone, so only a real fault crosses it.

### Vibration: 12 mm/s

Healthy joints vibrate at 1–3 mm/s, and worn joints in the history reach about 10 mm/s. General machine vibration charts (ISO 10816 style) treat values above roughly 11 mm/s as levels that cause damage. 12 mm/s is just above that and above the worst worn reading.

### Why the check is separate from the model

- It is plain comparisons with no training, randomness or probabilities, so the same input always gives the same answer.
- It runs on every joint before the model is used, and an arm that fails it is stopped no matter what the model says.
- `python3 arm_monitor.py --no-model` shows that ARM-04 and ARM-05 are still stopped with the model turned off.

### Limitations

The data is synthetic, so these numbers fit the dataset and are not taken from a real arm. On a real fleet, the limits would come from the motor and gearbox datasheets.

## 2. How the model and the maintenance log combine

Two independent signals feed the final decision.

**Wear risk (model).** A RandomForest trained on `joint_history.csv` gives each joint a probability of being worn. The arm uses the highest of its three joints, because one bad joint is enough to put the arm at risk.

**Note score (maintenance log).** The log is scanned for lines that name an arm, such as `ARM-03`. Lines that name no arm (the coffee machine, a training reminder) are ignored.

| Word type | Examples | Points |
|---|---|---|
| Severe | grinding, burning, smoke, sparks, cracked, seized | 3 |
| Mild | squeak, noise, rough, backlash, play, hot, rattle, loose, leak | 1 |

A keyword right after "no", "not" or "without" is skipped, so "no noise and no play" scores 0. Points are added up for each arm.

### Decision rules

The rules are checked top to bottom, and the first match wins.

| Order | Decision | When |
|---|---|---|
| 1 | EMERGENCY_STOP | Any safety limit is crossed |
| 2 | SCHEDULE_MAINTENANCE | Spoof found, note score 3 or more, or wear risk 0.7 or more |
| 3 | SCHEDULE_MAINTENANCE | Note score 1 or more and wear risk 0.4 or more, so both signals agree |
| 4 | MONITOR | Note score 1 or more, or wear risk 0.4 or more |
| 5 | SAFE | Nothing above |

### Why it works this way

- **Either signal can act alone.** Technicians notice things sensors can't measure, like a smell or a sound. The model notices slow drift a person can miss. If only the model could trigger maintenance, the log would add nothing.
- **Severe words go straight to maintenance.** "Grinding" or "burning" describes damage that is already happening, so waiting for the model to agree is not worth the risk.
- **Agreement escalates.** A mild note or a medium wear risk alone is only worth watching. When both point the same way at once, it is more likely to be real, so the arm moves up to maintenance.
- **If the model fails, the notes still count.** Wear risk becomes `n/a` and the decision uses the notes, the spoof check and the safety stop.

### Results from the sample run

| Arm | Wear risk | Note score | Decision |
|---|---|---|---|
| ARM-01 | 0.10 | 0 ("no noise") | SAFE |
| ARM-02 | 0.01 | 1 (squeak) | MONITOR |
| ARM-03 | 0.91 | 6 (grinding, noise, hot, backlash) | SCHEDULE_MAINTENANCE |
| ARM-04 | 0.32 | 0 | EMERGENCY_STOP (wrist at 91 °C) |
| ARM-05 | 0.19 | 4 (rough, burning) | EMERGENCY_STOP (spoof caught) |

### Limitations

- Keyword matching does not understand sentences. "Grinding was fixed yesterday" still scores 3.
- Negation only looks at the one word before the keyword.
- Old notes count as much as new ones, and a note is linked to the whole arm, not a single joint.

## 3. How the spoofed-sensor defense works

### The idea

A joint motor's torque is tied to the current it draws:

```
torque ≈ current × Kt
```

`Kt` is the motor's torque constant: 8.0 Nm/A for the shoulder, 5.0 for the elbow and 1.6 for the wrist. The torque sensor and the current sensor are separate devices, so they act as a check on each other.

### The steps

1. For every joint, work out the expected torque: `current × Kt`.
2. If the reported torque differs from the expected torque by more than 25%, flag the torque sensor as spoofed.
3. Use the higher of the two values (reported or expected) for the safety check and the model. The system assumes the worst case instead of trusting either sensor.
4. A spoofed arm gets at least SCHEDULE_MAINTENANCE, because a sensor that can't be trusted needs checking. If the worst-case torque crosses a limit, the arm gets EMERGENCY_STOP.

The 25% tolerance leaves room for normal differences between the two sensors, like friction, gear losses and temperature changing `Kt` a little.

### Example: ARM-05

| | Value |
|---|---|
| Reported shoulder torque | 105 Nm (looks normal) |
| Motor current | 24 A |
| Expected torque | 24 × 8.0 = 192 Nm |
| Difference | 45%, over the 25% tolerance |
| Torque used | 192 Nm, over the 180 Nm limit |
| Decision | EMERGENCY_STOP |

Without the check, ARM-05 would have passed the safety stop with a fake normal reading.

### What it catches

- A fake low torque value that hides an overload. This is the attack in the task.
- A fake high torque value. It gets flagged too, though here it only causes an unneeded stop, which is the safe side to fail on.
- A frozen or replayed torque value while the real load changes, as long as the current changes with it.
- A torque sensor that is broken or stuck, even when nobody is attacking.

### What it does not catch

- **Both sensors spoofed together.** If the attacker also fakes the current so the pair still matches, the check passes.
- **Small spoofs inside the 25% tolerance.** For ARM-05, a fake value of 144 Nm or more would pass the check. The real 192 Nm would then be hidden behind a value under the 180 Nm limit. The tolerance creates a band the attacker can hide in.
- **Spoofed temperature or vibration.** Only torque has a second sensor to compare against. Temperature and vibration are taken as reported.
- **Replaying an older matching pair** of torque and current readings from a time when the arm was healthy.

### How it could be made stronger

- Compare torque with the torque the robot controller commanded, which gives a third independent source.
- Flag readings that stay perfectly flat or jump in ways a real joint can't.
- Sign sensor messages so faked or replayed packets can be rejected.
- Narrow the tolerance once real sensor data shows how closely the two sensors normally agree.
