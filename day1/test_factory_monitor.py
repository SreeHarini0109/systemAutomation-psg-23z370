import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hands_on_starter import evaluate_rules, identify_machine_for_attention, RULES


def test_rule_priority_is_respected():
    reading = {
        "temperature": 95,
        "pressure": 130,
        "vibration": 4.2,
        "current": 19,
    }
    rule_name, action = evaluate_rules(reading, RULES)
    assert rule_name == "CRITICAL_TEMP"
    assert action == "STOP_MACHINE"


def test_factory_identifies_most_urgent_machine():
    machines = {
        "M1": {"temperature": 70, "pressure": 110, "vibration": 2.0, "current": 8},
        "M2": {"temperature": 92, "pressure": 100, "vibration": 1.0, "current": 9},
        "M3": {"temperature": 78, "pressure": 132, "vibration": 4.7, "current": 12},
        "M4": {"temperature": 81, "pressure": 109, "vibration": 3.0, "current": 14},
        "M5": {"temperature": 53, "pressure": 90, "vibration": 1.0, "current": 6},
    }

    machine_id, rule_name, action = identify_machine_for_attention(machines)
    assert machine_id == "M2"
    assert rule_name == "CRITICAL_TEMP"
    assert action == "STOP_MACHINE"


def test_factory_resolves_same_priority_tie_by_machine_id():
    machines = {
        "M3": {"temperature": 95, "pressure": 100, "vibration": 1.0, "current": 10},
        "M1": {"temperature": 95, "pressure": 100, "vibration": 1.0, "current": 10},
    }

    machine_id, rule_name, action = identify_machine_for_attention(machines)
    assert machine_id == "M1"
    assert rule_name == "CRITICAL_TEMP"
    assert action == "STOP_MACHINE"
