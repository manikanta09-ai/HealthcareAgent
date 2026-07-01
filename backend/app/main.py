import asyncio
import json
import logging
import uuid
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import settings
from app.db import (
    init_db,
    create_conversation,
    get_conversations,
    rename_conversation,
    delete_conversation,
    add_message,
    get_messages
)
from app.executors.context import active_queue
from app.executors.ai_executor import ai_executor
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.agents.graph import build_graph

# Global checkpointer context and graph instances
checkpointer_context = None
graph = None

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="Symptom Triage Assistant API", version="1.0.0")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev simplicity, restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Chat"

class RenameConversationRequest(BaseModel):
    title: str

class MessageRequest(BaseModel):
    message: str

@app.on_event("startup")
async def startup_event():
    global checkpointer_context, graph
    logger.info("Initializing Database...")
    init_db()
    
    logger.info("Initializing Async Checkpointer & Graph...")
    checkpointer_context = AsyncSqliteSaver.from_conn_string(settings.CHECKPOINTS_PATH)
    saver = await checkpointer_context.__aenter__()
    graph = build_graph(saver)

@app.on_event("shutdown")
async def shutdown_event():
    global checkpointer_context
    if checkpointer_context:
        logger.info("Closing Async Checkpointer connection...")
        await checkpointer_context.__aexit__(None, None, None)

@app.get("/api/conversations")
def list_conversations():
    """Retrieve list of conversation history."""
    try:
        return get_conversations()
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conversations")
def start_conversation(req: CreateConversationRequest):
    """Start a new triage session."""
    try:
        conv_id = str(uuid.uuid4())
        conv = create_conversation(conv_id, req.title)
        return conv
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/conversations/{conversation_id}")
def rename_chat(conversation_id: str, req: RenameConversationRequest):
    """Rename a conversation session."""
    try:
        rename_conversation(conversation_id, req.title)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error renaming conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/conversations/{conversation_id}")
def delete_chat(conversation_id: str):
    """Delete a conversation session and all its message history."""
    try:
        delete_conversation(conversation_id)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conversation_id}/messages")
def list_messages(conversation_id: str):
    """Retrieve message history for a conversation."""
    try:
        return get_messages(conversation_id)
    except Exception as e:
        logger.error(f"Error retrieving messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_title_from_message(message: str) -> str:
    """Uses LLM to summarize user's symptom message into a short 3-5 word title."""
    try:
        messages = [
            SystemMessage(content="You are a text summarizer. Summarize the patient's symptoms into a short, concise, and clean title of exactly 2 to 4 words. Do not use quotes or punctuation."),
            HumanMessage(content=f"Message: {message}\n\nTitle:")
        ]
        response = await ai_executor.execute_llm(
            agent_name="title_generator",
            model_name=settings.ROUTER_MODEL,
            messages=messages,
            temperature=0.3
        )
        title = response.content.strip().strip('"').strip("'")
        return title if len(title) > 2 else "Symptom Triage"
    except Exception as e:
        logger.error(f"Failed to generate title: {e}")
        return message[:30] + "..." if len(message) > 30 else message

@app.post("/api/conversations/{conversation_id}/message")
async def send_message_stream(conversation_id: str, req: MessageRequest):
    """
    Submits user message and streams assistant response via SSE (Server-Sent Events).
    """
    logger.info(f"Received stream request for conversation {conversation_id}")
    
    # 1. Fetch current message history from SQLite
    db_messages = get_messages(conversation_id)
    
    # 2. Automatically generate title if it is the first user message
    # Let's count user messages
    user_msg_count = sum(1 for m in db_messages if m["role"] == "user")
    if user_msg_count == 0:
        # Generate and update title asynchronously or inline
        title = await generate_title_from_message(req.message)
        rename_conversation(conversation_id, title)
        logger.info(f"Generated title for chat: {title}")

    # 3. Format message history for LangGraph
    history = []
    for msg in db_messages:
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            history.append(AIMessage(content=msg["content"]))

    # 4. Save the new user message to SQLite database
    add_message(conversation_id, "user", req.message)
    # Append the new message to history
    history.append(HumanMessage(content=req.message))

    # 5. Define graph configuration
    config = {"configurable": {"thread_id": conversation_id}}
    
    # 6. Check if graph has active checkpoints and is paused at an interrupt
    state = await graph.aget_state(config)
    is_paused = len(state.next) > 0

    async def event_generator():
        # Setup local queue for SSE streaming
        queue = asyncio.Queue()
        # Bind the queue to the context variable so AIExecutor can read it
        active_queue.set(queue)

        # Run the graph execution in a background task
        if is_paused:
            logger.info("Resuming paused LangGraph workflow with new user message.")
            # Update state with the new message
            await graph.aupdate_state(config, {"messages": [HumanMessage(content=req.message)]})
            task = asyncio.create_task(graph.ainvoke(None, config))
        else:
            logger.info("Starting new LangGraph workflow execution.")
            task = asyncio.create_task(graph.ainvoke({"messages": history}, config))

        try:
            while True:
                # 1. Drain the queue first
                while not queue.empty():
                    event = await queue.get()
                    yield f"data: {json.dumps(event)}\n\n"
                
                # 2. Check if the task is done
                if task.done():
                    # Check queue one last time
                    if queue.empty():
                        break
                
                # 3. Non-blocking wait for items
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    pass
            
            # Wait for task to throw exceptions if any occurred
            await task
            
            # 7. Grab the final state of the graph
            final_state = await graph.aget_state(config)
            
            # Case A: Paused on clarifying question
            if final_state.values.get("clarifying_question"):
                question = final_state.values.get("clarifying_question")
                add_message(conversation_id, "assistant", question)
                yield f"data: {json.dumps({'type': 'clarification', 'question': question})}\n\n"
                logger.info("Graph paused: awaiting user clarification.")
                
            # Case B: Finished. Final report compiled
            elif final_state.values.get("final_report"):
                report = final_state.values.get("final_report")
                add_message(conversation_id, "assistant", report)
                yield f"data: {json.dumps({'type': 'complete', 'report': report})}\n\n"
                logger.info("Graph finished: triage report completed.")
            else:
                logger.warning("Graph completed but neither report nor clarifying question was set.")
                
        except Exception as e:
            logger.error(f"Error during stream generation: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Internal execution error: {str(e)}'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Serve static frontend files if built
dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
if os.path.exists(dist_path):
    logger.info(f"Mounting frontend static files from: {dist_path}")
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")

    @app.get("/{catchall:path}")
    async def serve_frontend(catchall: str):
        if catchall.startswith("api/") or catchall.startswith("docs") or catchall.startswith("openapi.json"):
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse(os.path.join(dist_path, "index.html"))

if __name__ == "__main__":
    import uvicorn
    # Initialize DB
    init_db()
    # Run uvicorn server
    uvicorn.run(app, host="0.0.0.0", port=8000)
