from typing import Dict, List, Any, Optional

SYMPTOM_DB = {
    "fever": {
        "conditions": ["Influenza (Flu)", "Common Cold", "COVID-19", "Gastroenteritis", "UTI", "Meningitis"],
        "description": "An elevation in body temperature, often in response to infection.",
        "red_flags": ["Fever above 103°F (39.4°C)", "Fever lasting more than 7 days", "Fever accompanied by stiff neck, confusion, or breathing difficulty."],
        "respiratory_related": False
    },
    "cough": {
        "conditions": ["Bronchitis", "Asthma", "Common Cold", "Pneumonia", "COVID-19", "GERD"],
        "description": "A reflex action to clear the airways of mucus, irritants, or foreign particles.",
        "red_flags": ["Coughing up blood", "Shortness of breath or breathing difficulty", "Cough lasting more than 3 weeks."],
        "respiratory_related": True
    },
    "headache": {
        "conditions": ["Tension Headache", "Migraine", "Sinusitis", "Dehydration", "Meningitis", "Hypertension"],
        "description": "Pain or discomfort in the head, scalp, or neck region.",
        "red_flags": ["Sudden, severe headache ('thunderclap')", "Headache with fever, stiff neck, confusion, or vision changes", "Headache after a head injury."],
        "respiratory_related": False
    },
    "breathing difficulty": {
        "conditions": ["Asthma Flare-up", "Pneumonia", "COPD Exacerbation", "Anaphylaxis (Severe Allergy)", "Pulmonary Embolism", "Heart Failure"],
        "description": "Shortness of breath, rapid breathing, or feeling unable to get enough air.",
        "red_flags": ["Severe breathing distress", "Bluish lips or face (cyanosis)", "Chest pain or pressure", "Sudden onset."],
        "respiratory_related": True
    },
    "chest pain": {
        "conditions": ["Angina", "Myocardial Infarction (Heart Attack)", "Pleurisy", "Costochondritis", "Panic Attack", "GERD"],
        "description": "Discomfort or pain anywhere from the neck to the upper abdomen.",
        "red_flags": ["Pain radiating to jaw, neck, back, or left arm", "Pain accompanied by sweating, nausea, shortness of breath, or dizziness", "Crushing or squeezing pressure."],
        "respiratory_related": True
    },
    "cold": {
        "conditions": ["Rhinovirus (Common Cold)", "Allergic Rhinitis", "Sinus Infection"],
        "description": "A viral infection of the upper respiratory tract, causing runny nose, congestion, sneezing.",
        "red_flags": ["Symptoms lasting more than 10-14 days without improvement", "Difficulty breathing."],
        "respiratory_related": True
    },
    "sore throat": {
        "conditions": ["Pharyngitis (Viral)", "Strep Throat (Bacterial)", "Tonsillitis", "Mononucleosis"],
        "description": "Pain, itchiness, or irritation in the throat, often worse when swallowing.",
        "red_flags": ["Difficulty breathing or swallowing", "Inability to open mouth fully", "High fever."],
        "respiratory_related": True
    }
}

def lookup_symptoms(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Looks up symptoms in the local database.
    Can be filtered by 'respiratory_only' for the respiratory specialist.
    Input format: {"symptoms": ["cough", "fever"], "respiratory_only": bool}
    """
    symptoms = params.get("symptoms", [])
    respiratory_only = params.get("respiratory_only", False)
    
    results = {}
    for symptom in symptoms:
        symptom_lower = symptom.lower().strip()
        # Direct lookup or substring match
        matched_key = None
        for key in SYMPTOM_DB:
            if key in symptom_lower or symptom_lower in key:
                matched_key = key
                break
                
        if matched_key:
            data = SYMPTOM_DB[matched_key]
            if respiratory_only and not data["respiratory_related"]:
                continue
            results[matched_key] = data
            
    return {
        "matched_count": len(results),
        "results": results,
        "notes": "Filtered for respiratory conditions only." if respiratory_only else "General physician lookup."
    }
