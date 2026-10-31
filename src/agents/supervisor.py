from typing import Literal
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, MessagesState
from src.config import settings
from src.agents.workers import sql_worker_node, risk_worker_node

llm = ChatOllama(model=settings.OLLAMA_MODEL, temperature=settings.OLLAMA_TEMPERATURE)

def supervisor_node(state: MessagesState):
    """Central manager node that decides which specialist worker should handle the request next."""
    messages = state["messages"]
    
    supervisor_prompt = SystemMessage(
        content=(
            "You are a Supply Chain Engineering Supervisor managing two specialist workers:\n"
            "1. 'sql_worker': Handles inventory stock, product catalogs, multi-table joins, warehouse locations, and purchase order lookups.\n"
            "2. 'risk_worker': Handles supplier performance ratings, delivery delay analytics, lead times, and vendor risk scores.\n\n"
            "Analyze the user's latest request and reply ONLY with the exact name of the worker who should handle it next: 'sql_worker' or 'risk_worker'. "
            "If the task is already fully answered, reply with 'FINISH'."
        )
    )
    
    response = llm.invoke([supervisor_prompt] + messages)
    return {"messages": [response]}

def router_decision(state: MessagesState) -> Literal["sql_worker", "risk_worker", "__end__"]:
    """Route execution based on the supervisor's decision or keyword fallback."""
    messages = state["messages"]
    last_message = messages[-1]
    content = last_message.content.strip().lower()
    
    if "risk" in content or "supplier rating" in content or "delay analysis" in content:
        return "risk_worker"
    elif "sql" in content or "inventory" in content or "stock" in content or "warehouse" in content or "price" in content:
        return "sql_worker"
    
    # Fallback to inspecting the original user prompt
    user_prompt = ""
    for msg in messages:
        if isinstance(msg, HumanMessage):
            user_prompt = msg.content.lower()
            break
            
    if any(kw in user_prompt for kw in ["risk", "delay", "rating", "reliable"]):
        return "risk_worker"
        
    return "sql_worker"

# Build Simplified Supervisor Graph
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

compiled_graph = workflow.compile()