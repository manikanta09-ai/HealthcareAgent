import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Type, Union
from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.callbacks import BaseCallbackHandler
from app.config import settings

# Setup standard logger
logger = logging.getLogger("ai_executor")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

class SyncTokenQueueCallback(BaseCallbackHandler):
    """
    Synchronous callback handler that runs in the LLM execution thread.
    Safely pushes tokens to the main event loop's async queue.
    """
    def __init__(self, queue: asyncio.Queue, agent_name: str, loop: asyncio.AbstractEventLoop):
        self.queue = queue
        self.agent_name = agent_name
        self.loop = loop

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        # Schedule the coroutine in the main event loop from the thread
        asyncio.run_coroutine_threadsafe(
            self.queue.put({
                "type": "token",
                "agent": self.agent_name,
                "token": token
            }),
            self.loop
        )

class AIExecutor:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL

    async def execute_llm(
        self,
        agent_name: str,
        model_name: str,
        messages: List[BaseMessage],
        temperature: float = 0.1,
        json_mode: bool = False,
        queue: Optional[asyncio.Queue] = None,
        retries: int = 2,
        timeout: float = 45.0
    ) -> BaseMessage:
        """
        Executes the LLM in a separate thread to prevent blocking the FastAPI event loop.
        Uses thread-safe callbacks to stream tokens back to the client.
        """
        llm_kwargs = {
            "base_url": self.base_url,
            "model": model_name,
            "temperature": temperature,
            "timeout": timeout,
        }
        
        if json_mode:
            llm_kwargs["format"] = "json"

        llm = ChatOllama(**llm_kwargs).with_config(
            metadata={
                "agent_name": agent_name
            }
        )

        # Retrieve the running event loop
        loop = asyncio.get_running_loop()
        
        from app.executors.context import active_queue
        callbacks = []
        resolved_queue = queue or active_queue.get()
        if resolved_queue is not None:
            callbacks.append(SyncTokenQueueCallback(resolved_queue, agent_name, loop))

        start_time = time.time()
        last_exception = None

        for attempt in range(retries + 1):
            try:
                logger.info(
                    f"[AI_CALL_START] Agent: {agent_name} | Model: {model_name} | "
                    f"Attempt: {attempt + 1}/{retries + 1} | Prompt Messages Count: {len(messages)}"
                )
                
                # Execute standard langchain invocation inside a separate worker thread
                # This releases the FastAPI main event loop so it can stream SSE events.
                response = await asyncio.to_thread(
                    llm.invoke, 
                    messages, 
                    config={"callbacks": callbacks}
                )
                
                duration = time.time() - start_time
                logger.info(
                    f"[AI_CALL_SUCCESS] Agent: {agent_name} | Model: {model_name} | "
                    f"Duration: {duration:.2f}s | Output Length: {len(response.content)}"
                )
                return response

            except Exception as e:
                duration = time.time() - start_time
                last_exception = e
                logger.warning(
                    f"[AI_CALL_RETRY] Agent: {agent_name} | Model: {model_name} | "
                    f"Attempt {attempt + 1} failed | Error: {str(e)} | Duration: {duration:.2f}s"
                )
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)

        logger.error(
            f"[AI_CALL_FAILURE] Agent: {agent_name} | Model: {model_name} | "
            f"All retries failed. Error: {str(last_exception)}"
        )
        raise last_exception

ai_executor = AIExecutor()
