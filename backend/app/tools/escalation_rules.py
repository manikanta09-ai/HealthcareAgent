from typing import Dict, Any, List

def evaluate_escalation_rules(symptoms_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates symptoms against deterministic rules to determine risk level and recommended actions.
    Input structure:
    {
        "has_breathing_difficulty": bool,
        "fever_duration_days": int,
        "severity": str, (Mild, Moderate, Severe, Critical)
        "duration_days": int
    }
    """
    has_breathing_difficulty = symptoms_dict.get("has_breathing_difficulty", False)
    fever_duration_days = symptoms_dict.get("fever_duration_days", 0)
    severity = symptoms_dict.get("severity", "Mild").lower().strip()
    duration_days = symptoms_dict.get("duration_days", 0)
    
    red_flags = []
    urgency = "Low"
    recommendation = "Home monitoring, rest, and hydration. If symptoms persist or worsen, consult a healthcare provider."
    
    # 1. Critical breathing difficulty
    if has_breathing_difficulty:
        urgency = "Critical"
        red_flags.append("Breathing difficulty or shortness of breath reported.")
        recommendation = "IMMEDIATE ACTION REQUIRED: Please seek emergency medical care immediately (call 911 or visit the nearest Emergency Room)."
        
    # 2. High fever duration
    elif fever_duration_days > 7:
        urgency = "High"
        red_flags.append(f"Fever duration of {fever_duration_days} days exceeds the 7-day threshold.")
        recommendation = "URGENT MEDICAL ATTENTION: Please consult a physician or visit an urgent care clinic within the next 24 hours."
        
    # 3. Severe/Critical symptom presentation
    elif severity in ["severe", "critical"]:
        urgency = "High"
        red_flags.append(f"Symptom severity classified as {severity.upper()}.")
        recommendation = "MEDICAL EVALUATION RECOMMENDED: Schedule an appointment with a primary care physician or visit an urgent care center within 24 hours."
        
    # 4. Long symptom duration
    elif duration_days > 14:
        urgency = "Medium"
        red_flags.append(f"Total symptom duration of {duration_days} days exceeds 14 days.")
        recommendation = "PHYSICIAN FOLLOW-UP: Schedule a routine consultation with your primary care provider to evaluate these persistent symptoms."
        
    elif severity == "moderate" or fever_duration_days > 0 or duration_days > 3:
        urgency = "Medium"
        recommendation = "DOCTOR VISIT RECOMMENDED: Plan to see a primary care physician if symptoms do not start to improve in the next 48 hours."

    return {
        "urgency_score": urgency,
        "matched_red_flags": red_flags,
        "recommendation": recommendation,
        "disclaimer": "This escalation routing is based on deterministic rules and does not constitute formal medical diagnosis."
    }
