from typing import Dict, List, Any, Optional, Annotated
from typing_extensions import TypedDict
from pydantic import BaseModel
from langchain_core.messages import BaseMessage

# Define Pydantic models for structured data exchange
class StructuredSymptoms(BaseModel):
    complaint: str
    duration_days: int
    severity: str  # e.g., Mild, Moderate, Severe, Critical
    associated_symptoms: List[str]
    has_breathing_difficulty: bool
    has_high_fever: bool
    fever_duration_days: int

class SpecialistFindings(BaseModel):
    specialist_name: str
    assessment: str
    supporting_evidence: List[str]
    recommended_triage: str  # e.g., Low, Medium, High, Critical
    confidence_score: float

class RiskAssessment(BaseModel):
    urgency_score: str  # e.g., Low, Medium, High, Critical
    matched_red_flags: List[str]
    recommendation: str
    disclaimer: str

class ValidatorFeedback(BaseModel):
    approved: bool
    feedback: str
    target_specialist: Optional[str] = None

def merge_findings(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing)
    for k, v in new.items():
        merged[k] = v
    return merged

def merge_messages(existing: List[BaseMessage], new: List[BaseMessage]) -> List[BaseMessage]:
    return existing + new

class SymptomState(TypedDict):
    messages: Annotated[List[BaseMessage], merge_messages]
    symptoms: Optional[StructuredSymptoms]
    clarifying_question: Optional[str]
    specialists_to_invoke: List[str]
    specialist_findings: Annotated[Dict[str, SpecialistFindings], merge_findings]
    risk_score: Optional[RiskAssessment]
    validator_feedback: Optional[ValidatorFeedback]
    retry_counts: Dict[str, int]
    specialist_objections: Dict[str, str]
    final_report: Optional[str]
    current_stage: str
