from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from src.config import settings
from src.agents.workers import sql_worker_node, risk_worker_node

# Initialize LLM
llm = ChatOllama(model=settings.OLLAMA_MODEL, temperature=settings.OLLAMA_TEMPERATURE)

# 1. Define strict schema for production routing
class SupervisorRouter(BaseModel):
    next_worker: Literal["sql_worker", "risk_worker", "FINISH"] = Field(
        description="The next specialist worker to route to, or FINISH if the user request is completely resolved."
    )
    reasoning: str = Field(description="Brief explanation for the routing decision.")

# Bind structured output to the local model
structured_supervisor_llm = llm.with_structured_output(SupervisorRouter)

def supervisor_node(state: MessagesState):
    """Production supervisor using semantic structured outputs instead of keyword checks."""
    messages = state["messages"]
    
    supervisor_prompt = SystemMessage(
        content=(
            "You are a Supply Chain Engineering Supervisor managing two specialist workers:\n"
            "1. 'sql_worker': Handles inventory stock, product catalogs, multi-table joins, warehouse locations, and purchase order lookups.\n"
            "2. 'risk_worker': Handles supplier performance ratings, delivery delay analytics, lead times, and vendor risk scores.\n\n"
            "Analyze the conversation context and determine the correct next worker or select 'FINISH'."
        )
    )
    
    # The model returns a validated Pydantic object matching SupervisorRouter
    decision: SupervisorRouter = structured_supervisor_llm.invoke([supervisor_prompt] + messages)
    
    # Pass the routing directive along in a system message for the conditional router
    return {"messages": [SystemMessage(content=f"ROUTE_TO: {decision.next_worker} (Reason: {decision.reasoning})")]}

def router_decision(state: MessagesState) -> Literal["sql_worker", "risk_worker", "__end__"]:
    """Clean conditional routing based strictly on the supervisor's structured output."""
    messages = state["messages"]
    
    # Inspect recent messages for the supervisor's routing directive
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content:
            if "ROUTE_TO: sql_worker" in msg.content:
                return "sql_worker"
            elif "ROUTE_TO: risk_worker" in msg.content:
                return "risk_worker"
            elif "ROUTE_TO: FINISH" in msg.content:
                return "__end__"
            
    # Fallback default if unparseable
    return "sql_worker"

# Initialize Memory Saver for checkpointer / HITL persistence
memory = MemorySaver()

# Build Supervisor Graph
workflow = StateGraph(MessagesState)

# Add nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("sql_worker", sql_worker_node)
workflow.add_node("risk_worker", risk_worker_node)

# Set entry point
workflow.set_entry_point("supervisor")

# Conditional edges from supervisor
workflow.add_conditional_edges(
    "supervisor",
    router_decision,
    {
        "sql_worker": "sql_worker",
        "risk_worker": "risk_worker",
        "__end__": "__end__"
    }
)

# Workers complete the cycle and end execution cleanly
workflow.add_edge("sql_worker", "__end__")
workflow.add_edge("risk_worker", "__end__")

# EXPLICITLY DEFINE compiled_graph AT MODULE LEVEL
compiled_graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=[]
)