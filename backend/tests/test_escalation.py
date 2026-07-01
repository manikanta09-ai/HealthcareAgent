import sys
import os

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app.tools.escalation_rules import evaluate_escalation_rules

def test_escalation_critical():
    result = evaluate_escalation_rules({
        "has_breathing_difficulty": True,
        "fever_duration_days": 0,
        "severity": "Mild",
        "duration_days": 1
    })
    assert result["urgency_score"] == "Critical"
    assert "EMERGENCY" in result["recommendation"].upper()

def test_escalation_high_fever():
    result = evaluate_escalation_rules({
        "has_breathing_difficulty": False,
        "fever_duration_days": 8,
        "severity": "Mild",
        "duration_days": 8
    })
    assert result["urgency_score"] == "High"
    assert "URGENT" in result["recommendation"].upper()

def test_escalation_severe():
    result = evaluate_escalation_rules({
        "has_breathing_difficulty": False,
        "fever_duration_days": 2,
        "severity": "Severe",
        "duration_days": 3
    })
    assert result["urgency_score"] == "High"

def test_escalation_low():
    result = evaluate_escalation_rules({
        "has_breathing_difficulty": False,
        "fever_duration_days": 0,
        "severity": "Mild",
        "duration_days": 2
    })
    assert result["urgency_score"] == "Low"
