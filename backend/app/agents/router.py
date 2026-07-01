import json
import logging
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.state import SymptomState
from app.executors.ai_executor import ai_executor
from app.config import settings
from app.executors.context import update_stage

logger = logging.getLogger("router_agent")

ROUTER_PROMPT = """
You are a medical router supervisor. Your job is to classify the patient's symptoms and determine which clinical specialists must be consulted.
The available specialists are:
1. "general_physician": Handles general, systemic, infectious, and non-respiratory symptoms (e.g. fever, headache, body aches, digestive issues, general fatigue).
2. "respiratory_specialist": Handles upper and lower respiratory symptoms, chest pain, coughing, congestion, breathing difficulty, cold, sore throat, or lung issues.

You can select one or both specialists. If symptoms overlap, you MUST select both.
Provide your classification as a JSON object with a single key "specialists" containing a list of strings representing the selected specialists (e.g., ["general_physician"] or ["general_physician", "respiratory_specialist"]).

Example JSON Output:
{
  "specialists": ["general_physician", "respiratory_specialist"]
}
"""

async def router_node(state: SymptomState) -> Dict[str, Any]:
    """
    Router Agent Node: Decides which specialist nodes to invoke based on structured symptoms.
    """
    await update_stage("router", "Classifying symptoms and routing to specialists...")
    logger.info("Running Router Agent Node")
    symptoms = state.get("symptoms")
    if not symptoms:
        logger.warning("No structured symptoms found. Defaulting router to general_physician.")
        return {
            "specialists_to_invoke": ["general_physician"],
            "current_stage": "specialist_reasoning"
        }

    symptoms_summary = (
        f"Complaint: {symptoms.complaint}\n"
        f"Associated symptoms: {', '.join(symptoms.associated_symptoms)}\n"
        f"Breathing difficulty: {symptoms.has_breathing_difficulty}\n"
        f"Fever: {symptoms.has_high_fever} (duration {symptoms.fever_duration_days} days)"
    )

    router_messages = [
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=f"Symptoms summary:\n{symptoms_summary}\n\nSelect specialists:")
    ]

    response = await ai_executor.execute_llm(
        agent_name="router",
        model_name=settings.ROUTER_MODEL,
        messages=router_messages,
        json_mode=True,
        temperature=0.1
    )

    try:
        data = json.loads(response.content)
        specialists = data.get("specialists", ["general_physician"])
        # Clean and validate specialists
        valid_specialists = []
        for spec in specialists:
            spec_clean = spec.lower().strip()
            if spec_clean in ["general_physician", "respiratory_specialist"]:
                valid_specialists.append(spec_clean)
        
        if not valid_specialists:
            valid_specialists = ["general_physician"]
            
    except Exception as e:
        logger.error(f"Failed to parse router selection JSON: {e}. Raw content: {response.content}")
        valid_specialists = ["general_physician"]

    logger.info(f"Router selected specialists: {valid_specialists}")
    return {
        "specialists_to_invoke": valid_specialists,
        "current_stage": "specialist_reasoning"
    }
