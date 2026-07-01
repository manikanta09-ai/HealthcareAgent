import logging
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.state import SymptomState
from app.executors.ai_executor import ai_executor
from app.config import settings
from app.executors.context import update_stage

logger = logging.getLogger("compiler_agent")

COMPILER_PROMPT = """
You are a medical report compiler. Your job is to synthesize findings from medical specialists and risk assessors into a patient-facing symptom triage report.
The report MUST be structured in markdown with these exact headings:
1. ### 📋 Symptom Summary
2. ### 🔍 Clinical Specialist Findings
3. ### ⚠️ Urgency & Risk Level
4. ### 💡 Recommended Actions
5. ### 🛑 Medical Disclaimer

Rules:
- Under "Urgency & Risk Level", prominently display the computed Urgency Rating: {urgency_score} (e.g. **CRITICAL**, **HIGH**, **MEDIUM**, **LOW**).
- Under "Medical Disclaimer", you MUST include a standard medical disclaimer saying this is not medical advice, is for informational routing purposes only, and the patient should consult a physician.
- Synthesize the findings into clear, concise, and empathetic paragraphs. Do not use generic placeholders.

Inputs to compile:
Patient Symptoms:
{symptoms_summary}

Specialist Findings:
{specialist_findings}

Risk Assessor Evaluation:
{risk_evaluation}
"""

async def report_compiler_node(state: SymptomState) -> Dict[str, Any]:
    """
    Compiler Agent Node: Compiles the final structured triage report in markdown.
    Streams output to the user's active session queue if present.
    """
    await update_stage("report_compiler", "Compiling final triage report...")
    logger.info("Running Compiler Agent Node")
    symptoms = state.get("symptoms")
    findings = state.get("specialist_findings", {})
    risk = state.get("risk_score")
    
    # 1. Format symptoms summary
    symptoms_summary = (
        f"- Main Complaint: {symptoms.complaint if symptoms else 'Unspecified'}\n"
        f"- Duration: {symptoms.duration_days if symptoms else -1} days\n"
        f"- Reported Severity: {symptoms.severity if symptoms else 'Unknown'}\n"
        f"- Breathing Difficulty: {'Yes' if symptoms and symptoms.has_breathing_difficulty else 'No'}\n"
        f"- Fever: {'Yes' if symptoms and symptoms.has_high_fever else 'No'} "
        f"(duration: {symptoms.fever_duration_days if symptoms else 0} days)"
    )

    # 2. Format specialist findings
    specialist_summary = ""
    if not findings:
        specialist_summary = "No specialist assessments were successfully compiled."
    else:
        for spec_name, spec_data in findings.items():
            name_pretty = "General Physician" if spec_name == "general_physician" else "Respiratory Specialist"
            specialist_summary += (
                f"#### {name_pretty} (Confidence: {spec_data.confidence_score * 100:.0f}%)\n"
                f"- **Assessment**: {spec_data.assessment}\n"
                f"- **Supporting Evidence**: {', '.join(spec_data.supporting_evidence)}\n"
                f"- **Triage Suggestion**: {spec_data.recommended_triage}\n\n"
            )

    # 3. Format risk assessment
    urgency = risk.urgency_score if risk else "Low"
    risk_evaluation = (
        f"- **Urgency Score**: {urgency}\n"
        f"- **Matched Red Flags**: {', '.join(risk.matched_red_flags) if risk and risk.matched_red_flags else 'None'}\n"
        f"- **Primary Guidance**: {risk.recommendation if risk else ''}"
    )

    # 4. Invoke LLM to compile report
    prompt = COMPILER_PROMPT.format(
        urgency_score=urgency.upper(),
        symptoms_summary=symptoms_summary,
        specialist_findings=specialist_summary,
        risk_evaluation=risk_evaluation
    )

    # We will pass the queue so the final report streams to the user token-by-token!
    # The config dictionary contains the stream queue in 'configurable'.
    queue = None
    # Wait, we can get the queue from the execution thread config if needed, or pass it directly.
    # To make it clean, we can inspect state or pass a callback.
    # In LangGraph, when calling graph.stream(), we can read from config.
    # Let's write a helper to fetch queue from config.
    
    compiler_messages = [
        SystemMessage(content="You are a clinical report editor."),
        HumanMessage(content=prompt)
    ]

    response = await ai_executor.execute_llm(
        agent_name="report_compiler",
        model_name=settings.COMPILER_MODEL,
        messages=compiler_messages,
        temperature=0.3
    )

    report_content = response.content.strip()
    logger.info("Report Compiler completed report compilation successfully.")
    
    return {
        "final_report": report_content,
        "current_stage": "completed"
    }
