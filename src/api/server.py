from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from langchain_core.messages import HumanMessage, AIMessage
from src.agents.supervisor import compiled_graph
from src.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise Supply Chain Multi-Agent REST API",
    version="1.0.0"
)

class QueryRequest(BaseModel):
    prompt: str

class QueryResponse(BaseModel):
    prompt: str
    response: str
    trace: List[str]

@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": settings.APP_NAME,
        "model": settings.OLLAMA_MODEL
    }

@app.post("/api/v1/query", response_model=QueryResponse)
def execute_agent_query(request: QueryRequest):
    try:
        if not request.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
            
        inputs = {"messages": [HumanMessage(content=request.prompt)]}
        
        trace_steps = []
        final_response = "No response generated."
        
        # Execute the graph once using stream to capture both trace and final state
        for event in compiled_graph.stream(inputs, stream_mode="updates"):
            for node_name, node_output in event.items():
                if node_name == "supervisor":
                    trace_steps.append("👔 **Supervisor Node**: Evaluated intent and routed execution.")
                elif node_name == "sql_worker":
                    trace_steps.append("🔍 **SQL Specialist Worker**: Formulating database query strategy...")
                elif node_name == "sql_tools":
                    trace_steps.append("⚡ **SQL Execution Tool**: Executing read-only query on enterprise SQLite DB...")
                elif node_name == "risk_worker":
                    trace_steps.append("🛡️ **Supplier Risk Analyst Worker**: Assessing vendor metrics...")
                elif node_name == "risk_tools":
                    trace_steps.append("⚡ **Risk Analysis Tool**: Computing delay statistics and risk tiers...")
                
                # Extract latest message content if available
                if "messages" in node_output and node_output["messages"]:
                    latest_msg = node_output["messages"][-1]
                    if isinstance(latest_msg, AIMessage) and latest_msg.content:
                        # Ensure we don't capture raw JSON tool-call strings as final answers
                        content = latest_msg.content.strip()
                        if not content.startswith("{") and not content.startswith("["):
                            final_response = content

        # Fallback: if final_response wasn't captured from stream updates, invoke once
        if final_response == "No response generated.":
            final_state = compiled_graph.invoke(inputs)
            if final_state["messages"]:
                last_msg = final_state["messages"][-1]
                if hasattr(last_msg, "content") and last_msg.content:
                    final_response = last_msg.content

        return QueryResponse(
            prompt=request.prompt,
            response=final_response,
            trace=trace_steps
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host=settings.API_HOST, port=settings.API_PORT, reload=settings.DEBUG)