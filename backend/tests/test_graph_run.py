import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.agents.graph import build_graph
from langchain_core.messages import HumanMessage

async def main():
    print("Starting Multi-Agent Graph Test Run...")
    
    checkpointer_context = AsyncSqliteSaver.from_conn_string("test_checkpoints.db")
    async with checkpointer_context as saver:
        graph = build_graph(saver)
        
        # Test input prompt (Critical case)
        user_message = (
            "I have had a high fever for 10 days, along with a mild headache, "
            "a persistent dry cough, a cold, and moderate chest pain. "
            "I am experiencing significant breathing difficulty."
        )
        
        config = {"configurable": {"thread_id": "test-thread-1"}}
        
        print("\n--> Invoking Graph with test prompt...")
        state_update = {"messages": [HumanMessage(content=user_message)]}
        result = await graph.ainvoke(state_update, config)
        
        print("\n--> Graph Execution Complete!")
        print(f"Final Stage Status: {result.get('current_stage')}")
        print("\n=== COMPILED TRIAGE REPORT CARD ===")
        print(result.get("final_report"))

if __name__ == "__main__":
    asyncio.run(main())
