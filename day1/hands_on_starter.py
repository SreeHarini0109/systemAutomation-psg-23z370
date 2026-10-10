"""
DAY 1 · HANDS-ON — Build Your Rule Engine
23IF02 System Automation

This version extends the original starter into a five-machine factory monitor.
The system checks every machine, applies safety rules in priority order, and
identifies the machine that needs immediate attention.
"""

import random
import time

LOG_FILE = "day1_log.txt"


# ---------------------------------------------------------------------------
# STEP 1 — Generate simulated sensor data
# ---------------------------------------------------------------------------
def generate_sensor_data():
    """Return a dict with realistic sensor values plus occasional noise."""
    temperature = random.uniform(50, 95)
    pressure = random.uniform(80, 130)
    vibration = random.uniform(0.2, 5.8)
    current = random.uniform(5, 22)

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
    }


# ---------------------------------------------------------------------------
# STEP 2 — Add domain rules with justified safety priorities
# These rules encode operating knowledge: overheated motors can fail fast,
# unsafe pressure can damage equipment, excessive vibration suggests imbalance,
# and current spikes indicate electrical stress.
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# STEP 3 — Detect machine state from the rules
# ---------------------------------------------------------------------------
def evaluate_rules(reading, rules):
    """Return (rule_name, action) for the first matching rule in priority order."""
    ordered_rules = sorted(rules, key=lambda rule: rule.get("priority", 999))

    for rule in ordered_rules:
        condition = rule.get("condition")
        if callable(condition) and condition(reading):
            return rule.get("name", "UNKNOWN_RULE"), rule.get("action", "CONTINUE_NORMAL")

    return "NO_RULE_FIRED", "CONTINUE_NORMAL"


def get_rule_priority(rule_name, rules):
    """Return the priority number for a rule name, or a safe fallback value."""
    for rule in rules:
        if rule.get("name") == rule_name:
            return rule.get("priority", 999)
    return 999


# ---------------------------------------------------------------------------
# STEP 4 — Trigger an action when a rule fires
# ---------------------------------------------------------------------------
def take_action(action):
    """Return a human-readable string describing what happens for this action."""
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


# ---------------------------------------------------------------------------
# STEP 5 — Log every decision made
# ---------------------------------------------------------------------------
def log_decision(machine_id, reading, rule_name, action):
    """Append a machine-specific decision to the log file."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as log_file:
        log_file.write(
            f"{timestamp} | machine={machine_id} | reading={reading} | rule={rule_name} | action={action}\n"
        )


def calculate_severity(reading):
    """Estimate how serious the reading is by combining the main sensor values."""
    temperature = reading.get("temperature")
    pressure = reading.get("pressure")
    vibration = reading.get("vibration")
    current = reading.get("current")

    score = 0
    if temperature is not None:
        score += max(0, temperature - 75) * 0.8
    if pressure is not None:
        score += max(0, pressure - 100) * 0.5
    if vibration is not None:
        score += max(0, vibration - 2.5) * 2.5
    if current is not None:
        score += max(0, current - 12) * 1.6
    return round(score, 2)


def identify_machine_for_attention(machines):
    """Return (machine_id, rule_name, action) for the machine needing attention first."""
    if not machines:
        return None, "NO_RULE_FIRED", "CONTINUE_NORMAL"

    candidates = []
    for machine_id, reading in machines.items():
        rule_name, action = evaluate_rules(reading, RULES)
        priority = get_rule_priority(rule_name, RULES) if rule_name != "NO_RULE_FIRED" else 999
        severity = calculate_severity(reading)
        candidates.append({
            "machine_id": machine_id,
            "rule_name": rule_name,
            "action": action,
            "priority": priority,
            "severity": severity,
        })

    selected = min(candidates, key=lambda item: (item["priority"], -item["severity"], item["machine_id"]))
    return selected["machine_id"], selected["rule_name"], selected["action"]


def generate_factory_data(machine_count=5):
    """Create a dictionary of machine IDs to sensor readings."""
    return {f"M{idx}": generate_sensor_data() for idx in range(1, machine_count + 1)}


# ---------------------------------------------------------------------------
# STEP 6 — Build a small factory monitor for five machines
# ---------------------------------------------------------------------------
def main():
    machines = generate_factory_data(5)

    print("=== FACTORY STATUS CHECK ===")
    for machine_id, reading in machines.items():
        rule_name, action = evaluate_rules(reading, RULES)
        outcome = take_action(action)
        print(f"{machine_id}: {reading} -> {rule_name} -> {outcome}")
        log_decision(machine_id, reading, rule_name, action)

    machine_id, rule_name, action = identify_machine_for_attention(machines)
    print("\n=== IMMEDIATE ATTENTION ===")
    if machine_id is None:
        print("No machine requires immediate attention.")
    else:
        print(f"Machine {machine_id} needs immediate attention.")
        print(f"Reason: {rule_name} -> {take_action(action)}")


if __name__ == "__main__":
    main()
