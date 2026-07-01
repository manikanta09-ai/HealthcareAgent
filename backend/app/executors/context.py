import contextvars
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("context")

# Context variables to track the active SSE stream queue
active_queue = contextvars.ContextVar("active_queue", default=None)

async def update_stage(stage_id: str, display_text: str):
    """
    Pushes a stage update event to the active queue.
    """
    q = active_queue.get()
    if q:
        try:
            await q.put({
                "type": "stage",
                "stage": stage_id,
                "text": display_text
            })
        except Exception as e:
            logger.error(f"Failed to push stage update to queue: {e}")
