import json
import logging
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.state import SymptomState, StructuredSymptoms
from app.executors.ai_executor import ai_executor
from app.config import settings

from app.executors.context import update_stage

logger = logging.getLogger("intake_agent")

INTAKE_PROMPT = """
You are a medical intake assistant. Your task is to extract structured symptom information from the patient's conversation history.
Analyze the conversation history and extract:
1. "complaint": The main health complaint described by the user.
2. "duration_days": The number of days the symptoms have persisted. If not mentioned or unclear, output -1.
3. "severity": The severity of the symptoms. Must be exactly one of: "Mild", "Moderate", "Severe", "Critical", or "Unknown". If not mentioned, output "Unknown".
4. "associated_symptoms": List of any secondary symptoms mentioned (e.g., headache, cold, cough, nausea).
5. "has_breathing_difficulty": Boolean (true/false) indicating if the patient mentions difficulty breathing, shortness of breath, or chest tightness.
6. "has_high_fever": Boolean (true/false) indicating if they mention a high temperature or high fever (typically > 101F / 38.3C).
7. "fever_duration_days": Number of days they have had a fever. Output 0 if no fever, or -1 if fever is mentioned but duration is not specified.

You must output your findings strictly as a JSON object with these exact keys. Do not include any explanation or markdown formatting, just raw JSON.

Example JSON output:
{
  "complaint": "fever and cold",
  "duration_days": 3,
  "severity": "Moderate",
  "associated_symptoms": ["cough", "runny nose"],
  "has_breathing_difficulty": false,
  "has_high_fever": false,
  "fever_duration_days": 3
}
"""

CLARIFYING_PROMPT = """
You are a medical intake assistant. The patient provided some symptoms, but critical details are missing:
Missing details: {missing_fields}

Ask a polite, single, focused clarifying question to ask the patient for this missing information.
Always include a brief note that this is not medical advice and is for routing purposes.
Keep it direct, warm, and professional.
"""

async def intake_node(state: SymptomState) -> Dict[str, Any]:
    """
    Intake Agent Node: Converts free text input into a structured symptom object.
    Identifies if critical details are missing, and generates a clarifying question if so.
    """
    await update_stage("intake", "Analyzing symptom description...")
    logger.info("Running Intake Agent Node")
    
    # 1. Compile message history for extraction
    messages = state.get("messages", [])
    history_str = ""
    for msg in messages:
        role = "Patient" if msg.type == "human" else "Assistant"
        history_str += f"{role}: {msg.content}\n"

    # 2. Extract structured symptoms using AI Executor in JSON mode
    extraction_messages = [
        SystemMessage(content=INTAKE_PROMPT),
        HumanMessage(content=f"Conversation history:\n{history_str}\n\nExtract the structured symptom details:")
    ]
    
    response = await ai_executor.execute_llm(
        agent_name="intake",
        model_name=settings.INTAKE_MODEL,
        messages=extraction_messages,
        json_mode=True,
        temperature=0.1
    )
    
    try:
        data = json.loads(response.content)
        symptoms = StructuredSymptoms(**data)
    except Exception as e:
        logger.error(f"Failed to parse structured symptoms JSON: {e}. Raw content: {response.content}")
        # Safe fallback
        symptoms = StructuredSymptoms(
            complaint="Unspecified complaint",
            duration_days=-1,
            severity="Unknown",
            associated_symptoms=[],
            has_breathing_difficulty=False,
            has_high_fever=False,
            fever_duration_days=0
        )

    # 3. Check for missing critical info
    missing_fields = []
    if symptoms.duration_days == -1:
        missing_fields.append("symptom duration (how many days)")
    if symptoms.severity == "Unknown":
        missing_fields.append("severity (mild, moderate, or severe)")
    if symptoms.has_high_fever and symptoms.fever_duration_days == -1:
        missing_fields.append("how long you have had the fever")

    if missing_fields:
        # Generate clarifying question
        fields_str = ", ".join(missing_fields)
        clarify_messages = [
            SystemMessage(content=CLARIFYING_PROMPT.format(missing_fields=fields_str)),
            HumanMessage(content="Generate the clarifying question:")
        ]
        clarify_resp = await ai_executor.execute_llm(
            agent_name="intake",
            model_name=settings.INTAKE_MODEL,
            messages=clarify_messages,
            temperature=0.5
        )
        
        question = clarify_resp.content.strip()
        logger.info(f"Missing critical details. Clarifying question: {question}")
        
        return {
            "symptoms": symptoms,
            "clarifying_question": question,
            "current_stage": "awaiting_clarification"
        }
    
    logger.info("Structured symptoms successfully extracted with no critical information missing.")
    return {
        "symptoms": symptoms,
        "clarifying_question": None,
        "current_stage": "routing"
    }
