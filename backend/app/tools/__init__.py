from app.executors.tool_executor import tool_executor
from app.tools.symptom_lookup import lookup_symptoms
from app.tools.escalation_rules import evaluate_escalation_rules

# Register the tools with the Tool Executor
tool_executor.register_tool("symptom_lookup", lookup_symptoms)
tool_executor.register_tool("escalation_rules", evaluate_escalation_rules)
