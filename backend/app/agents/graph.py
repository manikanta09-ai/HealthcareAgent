import logging
from typing import List, Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agents.state import SymptomState
from app.agents.intake import intake_node
from app.agents.router import router_node
from app.agents.specialists import general_physician_node, respiratory_specialist_node
from app.agents.risk_assessor import risk_assessor_node
from app.agents.validator import validator_node
from app.agents.compiler import report_compiler_node
import app.tools

logger = logging.getLogger("graph_builder")

# --- Dummy / Coordinator Nodes ---

def ask_clarification_node(state: SymptomState) -> Dict[str, Any]:
    """
    Dummy node that acts as a target for interrupts.
    Clears the clarifying question so that intake can re-run.
    """
    logger.info("Resuming from clarification interrupt node")
    return {
        "clarifying_question": None,
        "current_stage": "intake"
    }

def specialist_coordinator_node(state: SymptomState) -> Dict[str, Any]:
    """
    Dummy coordinator node. Acts as the entry point for both initial specialists routing
    and retry routing from the validator.
    """
    logger.info(f"Specialist coordinator routing to: {state.get('specialists_to_invoke')}")
    return {}


# --- Routing Decisions ---

def route_after_intake(state: SymptomState) -> str:
    """Routes to clarification pause or to supervisor router."""
    if state.get("clarifying_question"):
        return "ask_clarification"
    return "router"

def distribute_specialists(state: SymptomState) -> List[Send]:
    """Dynamic parallel fan-out using Send API based on specialists_to_invoke."""
    sends = []
    specs = state.get("specialists_to_invoke", [])
    for spec in specs:
        if spec == "general_physician":
            sends.append(Send("general_physician", state))
        elif spec == "respiratory_specialist":
            sends.append(Send("respiratory_specialist", state))
            
    if not sends:
        logger.warning("No specialists in list. Defaulting to general_physician.")
        sends.append(Send("general_physician", state))
        
    return sends

def route_after_validator(state: SymptomState) -> str:
    """Routes to retry specialist coordinator or compiles final report."""
    feedback = state.get("validator_feedback")
    if feedback and not feedback.approved:
        return "specialist_coordinator"
    return "report_compiler"


# --- Build Graph ---

def build_graph(checkpointer: AsyncSqliteSaver):
    builder = StateGraph(SymptomState)

    # Add Nodes
    builder.add_node("intake", intake_node)
    builder.add_node("ask_clarification", ask_clarification_node)
    builder.add_node("router", router_node)
    builder.add_node("specialist_coordinator", specialist_coordinator_node)
    builder.add_node("general_physician", general_physician_node)
    builder.add_node("respiratory_specialist", respiratory_specialist_node)
    builder.add_node("risk_assessor", risk_assessor_node)
    builder.add_node("validator", validator_node)
    builder.add_node("report_compiler", report_compiler_node)

    # Define Workflow Edges
    builder.add_edge(START, "intake")
    
    # Intake conditional routing
    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "ask_clarification": "ask_clarification",
            "router": "router"
        }
    )
    
    # Ask clarification returns to intake to evaluate follow-up text
    builder.add_edge("ask_clarification", "intake")
    
    # Router moves to specialist coordinator
    builder.add_edge("router", "specialist_coordinator")
    
    # Coordinator dynamically fans out in parallel
    builder.add_conditional_edges(
        "specialist_coordinator",
        distribute_specialists,
        {
            "general_physician": "general_physician",
            "respiratory_specialist": "respiratory_specialist"
        }
    )
    
    # Specialists join at the Risk Assessor
    builder.add_edge("general_physician", "risk_assessor")
    builder.add_edge("respiratory_specialist", "risk_assessor")
    
    # Risk Assessor leads to Validator
    builder.add_edge("risk_assessor", "validator")
    
    # Validator loops back to coordinator on rejection, or proceeds to compiler
    builder.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "specialist_coordinator": "specialist_coordinator",
            "report_compiler": "report_compiler"
        }
    )
    
    # Compiler finishes graph execution
    builder.add_edge("report_compiler", END)
    
    # Compile graph with interrupt *before* entering ask_clarification
    compiled_graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["ask_clarification"]
    ).with_config(
        metadata={
            "workflow_name": "symptom_triage_assistant"
        }
    )

    return compiled_graph
