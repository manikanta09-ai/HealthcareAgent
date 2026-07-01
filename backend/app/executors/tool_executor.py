import time
import logging
from typing import Callable, Dict, Any, Optional

# Setup standard logger
logger = logging.getLogger("tool_executor")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

class ToolExecutor:
    def __init__(self, tools_dict: Optional[Dict[str, Callable]] = None):
        self.tools = tools_dict or {}

    def register_tool(self, name: str, func: Callable):
        self.tools[name] = func

    async def execute_tool(
        self,
        tool_name: str,
        agent_name: str,
        tool_input: Any,
        config: Optional[dict] = None
    ) -> Any:
        """
        Executes a registered tool.
        Records: tool name, calling agent name, input, output, and duration.
        """
        if tool_name not in self.tools:
            logger.error(f"[TOOL_NOT_FOUND] Tool '{tool_name}' is not registered.")
            raise ValueError(f"Tool '{tool_name}' not found.")

        tool_func = self.tools[tool_name]
        start_time = time.time()
        
        logger.info(
            f"[TOOL_CALL_START] Tool: {tool_name} | Calling Agent: {agent_name} | "
            f"Input: {str(tool_input)[:500]}"
        )

        try:
            # Handle both async and sync tool executions
            if asyncio.iscoroutinefunction(tool_func):
                output = await tool_func(tool_input)
            else:
                output = tool_func(tool_input)

            duration = time.time() - start_time
            logger.info(
                f"[TOOL_CALL_SUCCESS] Tool: {tool_name} | Calling Agent: {agent_name} | "
                f"Duration: {duration:.4f}s | Output: {str(output)[:500]}"
            )
            return output

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[TOOL_CALL_FAILURE] Tool: {tool_name} | Calling Agent: {agent_name} | "
                f"Duration: {duration:.4f}s | Error: {str(e)}"
            )
            raise e

# Create a global instance of tool executor
tool_executor = ToolExecutor()
import asyncio
