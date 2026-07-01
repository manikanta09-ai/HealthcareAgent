import logging
from typing import Dict, Any
from app.agents.state import SymptomState, RiskAssessment, StructuredSymptoms
from app.executors.tool_executor import tool_executor
from app.executors.context import update_stage

logger = logging.getLogger("risk_assessor")

async def risk_assessor_node(state: SymptomState) -> Dict[str, Any]:
    """
    Risk Assessor Node: Deterministic, non-LLM node.
    Invokes the escalation_rules tool via the Tool Executor.
    """
    await update_stage("risk_assessor", "Evaluating urgency rules...")
    logger.info("Running Risk Assessor Node (Deterministic)")
    symptoms: StructuredSymptoms = state.get("symptoms")
    if not symptoms:
        logger.warning("No structured symptoms found for risk assessment. Defaulting to low risk.")
        risk_score = RiskAssessment(
            urgency_score="Low",
            matched_red_flags=[],
            recommendation="Please provide symptoms for a full evaluation.",
            disclaimer="Deterministic evaluation. Not medical advice."
        )
        return {"risk_score": risk_score, "current_stage": "validation"}

    # Prepare inputs for escalation_rules tool
    tool_input = {
        "has_breathing_difficulty": symptoms.has_breathing_difficulty,
        "fever_duration_days": symptoms.fever_duration_days,
        "severity": symptoms.severity,
        "duration_days": symptoms.duration_days
    }

    # Call deterministic rules tool via Tool Executor
    tool_output = await tool_executor.execute_tool(
        tool_name="escalation_rules",
        agent_name="risk_assessor",
        tool_input=tool_input
    )

    risk_score = RiskAssessment(
        urgency_score=tool_output.get("urgency_score", "Low"),
        matched_red_flags=tool_output.get("matched_red_flags", []),
        recommendation=tool_output.get("recommendation", ""),
        disclaimer=tool_output.get("disclaimer", "")
    )

    logger.info(f"Risk Assessor completed. Urgency: {risk_score.urgency_score}")
    return {
        "risk_score": risk_score,
        "current_stage": "validation"
    }
