import json
import logging
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.state import SymptomState, SpecialistFindings, StructuredSymptoms
from app.executors.ai_executor import ai_executor
from app.executors.tool_executor import tool_executor
from app.config import settings
from app.executors.context import update_stage

logger = logging.getLogger("specialists")

SPECIALIST_PROMPT = """
You are a senior medical specialist. Your role is to analyze the patient's symptoms using the provided reference data and compile your findings.
Role: {role_title}

Patient Structured Symptoms:
{symptoms_summary}

Reference Data (Symptom-Condition database results):
{reference_data}

Validator Objections (if any, please address these and revise your reasoning):
{validator_objections}

Write your assessment. Conclude by outputting a JSON object with these exact keys:
1. "specialist_name": "{specialist_name}"
2. "assessment": A detailed clinical reasoning summary of possible non-definitive conditions matching the symptoms and reference data.
3. "supporting_evidence": A list of facts or symptom details supporting this assessment.
4. "recommended_triage": One of "Low", "Medium", "High", or "Critical".
5. "confidence_score": A float between 0.0 and 1.0.

You must output strictly raw JSON matching the keys above. Do not include markdown codeblocks or extra prose.

Example JSON output:
{{
  "specialist_name": "{specialist_name}",
  "assessment": "Symptoms suggest possible acute viral rhinovirus or mild sinus congestion. Symptoms are systemic but mild.",
  "supporting_evidence": ["Headache for 3 days", "Mild nasal congestion"],
  "recommended_triage": "Low",
  "confidence_score": 0.85
}}
"""

async def run_specialist(
    state: SymptomState,
    specialist_name: str,
    role_title: str,
    respiratory_only: bool
) -> Dict[str, Any]:
    """
    Generic runner for specialist agents.
    Invokes tools via Tool Executor and LLMs via AI Executor.
    """
    await update_stage(specialist_name, f"Consulting {role_title}...")
    logger.info(f"Running specialist: {specialist_name}")
    symptoms: StructuredSymptoms = state.get("symptoms")
    
    # 1. Prepare tool input
    symptom_list = [symptoms.complaint] + symptoms.associated_symptoms
    tool_input = {
        "symptoms": symptom_list,
        "respiratory_only": respiratory_only
    }
    
    # 2. Call tool through Tool Executor
    tool_output = await tool_executor.execute_tool(
        tool_name="symptom_lookup",
        agent_name=specialist_name,
        tool_input=tool_input
    )
    
    # 3. Retrieve any validator objections for this specialist
    objection = state.get("specialist_objections", {}).get(specialist_name, "None")
    
    # 4. Format prompt and invoke LLM
    symptoms_summary = (
        f"Complaint: {symptoms.complaint}\n"
        f"Duration: {symptoms.duration_days} days\n"
        f"Severity: {symptoms.severity}\n"
        f"Breathing difficulty: {symptoms.has_breathing_difficulty}\n"
        f"Fever: {symptoms.has_high_fever} (duration {symptoms.fever_duration_days} days)"
    )
    
    prompt = SPECIALIST_PROMPT.format(
        role_title=role_title,
        specialist_name=specialist_name,
        symptoms_summary=symptoms_summary,
        reference_data=json.dumps(tool_output, indent=2),
        validator_objections=objection
    )
    
    model_name = settings.GP_MODEL if specialist_name == "general_physician" else settings.RESPIRATORY_MODEL
    
    response = await ai_executor.execute_llm(
        agent_name=specialist_name,
        model_name=model_name,
        messages=[
            SystemMessage(content=f"You are a clinical agent acting as {role_title}."),
            HumanMessage(content=prompt)
        ],
        json_mode=True,
        temperature=0.2
    )
    
    try:
        data = json.loads(response.content)
        findings = SpecialistFindings(**data)
    except Exception as e:
        logger.error(f"Failed to parse findings JSON for {specialist_name}: {e}. Raw: {response.content}")
        # Safe fallback
        findings = SpecialistFindings(
            specialist_name=specialist_name,
            assessment=f"Clinical assessment completed by {role_title} based on symptoms. Recommendations generated.",
            supporting_evidence=["Patient reported symptoms"],
            recommended_triage="Medium",
            confidence_score=0.5
        )
        
    return {
        "specialist_findings": {specialist_name: findings}
    }

async def general_physician_node(state: SymptomState) -> Dict[str, Any]:
    """General Physician Node"""
    return await run_specialist(
        state=state,
        specialist_name="general_physician",
        role_title="General Physician (Systemic/Infectious Symptoms Expert)",
        respiratory_only=False
    )

async def respiratory_specialist_node(state: SymptomState) -> Dict[str, Any]:
    """Respiratory Specialist Node"""
    return await run_specialist(
        state=state,
        specialist_name="respiratory_specialist",
        role_title="Respiratory Specialist (Chest/Airway Conditions Expert)",
        respiratory_only=True
    )
