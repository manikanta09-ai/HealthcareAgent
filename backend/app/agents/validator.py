import json
import logging
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.state import SymptomState, ValidatorFeedback, SpecialistFindings
from app.executors.ai_executor import ai_executor
from app.config import settings
from app.executors.context import update_stage

logger = logging.getLogger("validator_agent")

VALIDATOR_PROMPT = """
You are a clinical quality assurance validator. Your job is to audit the medical specialists' findings and the risk assessment to ensure safety and clinical standards.
Safety audit criteria:
1. NO DIAGNOSTIC OVERREACH: The specialist must NOT declare a definitive diagnosis (e.g., "You have pneumonia"). They must use non-definitive language (e.g., "symptoms are consistent with", "suggests possible", "may indicate").
2. INTERNAL CONSISTENCY: The specialist's findings must match the risk level. If the risk level is High or Critical, the findings must NOT suggest simple home rest as the only advice; they must recommend medical consultation.
3. MEDICAL DISCLAIMER: The findings or overall evaluation must explicitly mention a disclaimer that "this is not medical advice" or "consult a professional".

Specialist Findings:
{specialist_findings}

Risk Assessment:
{risk_assessment}

Verify if they meet all 3 criteria.
If all criteria are met, output:
{{"approved": true, "feedback": "All criteria satisfied.", "target_specialist": null}}

If any criteria are violated, output:
{{"approved": false, "feedback": "<detailed objection explaining what was violated and how to correct it>", "target_specialist": "<name of the specialist that failed: 'general_physician' or 'respiratory_specialist'>"}}

You must output strictly raw JSON matching the keys above. Do not include markdown formatting or extra text.
"""

async def validator_node(state: SymptomState) -> Dict[str, Any]:
    """
    Validator Agent Node: Validates the outputs of specialist nodes.
    Supports re-routing and capping retries.
    """
    await update_stage("validator", "Auditing specialist reports for safety and quality...")
    logger.info("Running Validator Agent Node")
    findings = state.get("specialist_findings", {})
    risk = state.get("risk_score")
    retry_counts = state.get("retry_counts", {})
    specialist_objections = state.get("specialist_objections", {})

    # Format findings and risk for validator LLM review
    findings_summary = ""
    for spec_name, spec_data in findings.items():
        findings_summary += (
            f"Specialist: {spec_name}\n"
            f"Assessment: {spec_data.assessment}\n"
            f"Recommended Triage: {spec_data.recommended_triage}\n"
            f"Supporting Evidence: {', '.join(spec_data.supporting_evidence)}\n\n"
        )

    risk_summary = (
        f"Urgency Score: {risk.urgency_score if risk else 'Unknown'}\n"
        f"Recommendation: {risk.recommendation if risk else ''}\n"
        f"Disclaimer: {risk.disclaimer if risk else ''}"
    )

    validator_messages = [
        SystemMessage(content=VALIDATOR_PROMPT.format(
            specialist_findings=findings_summary,
            risk_assessment=risk_summary
        )),
        HumanMessage(content="Audit the clinical findings and return JSON:")
    ]

    response = await ai_executor.execute_llm(
        agent_name="validator",
        model_name=settings.VALIDATOR_MODEL,
        messages=validator_messages,
        json_mode=True,
        temperature=0.1
    )

    try:
        data = json.loads(response.content)
        feedback = ValidatorFeedback(**data)
    except Exception as e:
        logger.error(f"Failed to parse validator feedback JSON: {e}. Raw: {response.content}")
        # Safe fallback: approve to prevent infinite loops on parsing issues
        feedback = ValidatorFeedback(approved=True, feedback="Fallback approval due to parse error.")

    logger.info(f"Validator decision: Approved={feedback.approved} | Target: {feedback.target_specialist}")

    if not feedback.approved and feedback.target_specialist:
        target = feedback.target_specialist.lower().strip()
        current_retries = retry_counts.get(target, 0)
        
        if current_retries < 2:
            # Increment retries and mark for re-invocation
            new_retry_counts = dict(retry_counts)
            new_retry_counts[target] = current_retries + 1
            
            new_objections = dict(specialist_objections)
            new_objections[target] = feedback.feedback
            
            logger.info(f"Validator REJECTED {target}. Retry count: {current_retries + 1}/2. Routing back to specialist.")
            return {
                "validator_feedback": feedback,
                "retry_counts": new_retry_counts,
                "specialist_objections": new_objections,
                "specialists_to_invoke": [target],
                "current_stage": "specialist_reasoning"
            }
        else:
            logger.warning(f"Validator REJECTED {target}, but retry limit (2) exceeded. Forcing compiler compilation.")
            feedback.approved = True
            feedback.feedback = "Retry limit exceeded. Safe compiler fallback will be used."

    return {
        "validator_feedback": feedback,
        "current_stage": "compiling_report"
    }
