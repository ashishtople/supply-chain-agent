import re
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_ollama import ChatOllama
from src.config import settings
from src.tools.sql_tools import query_supply_chain_db, get_pruned_schema
from src.tools.risk_tools import analyze_supplier_risk_metrics

llm = ChatOllama(model=settings.OLLAMA_MODEL, temperature=settings.OLLAMA_TEMPERATURE)

# ==========================================
# 1. SQL DATABASE SPECIALIST WORKER
# ==========================================
def sql_worker_node(state):
    """SQL worker with sliding conversational memory and filtered historical tool output."""
    messages = state["messages"]
    
    # Extract latest user query
    user_query = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_query = msg.content
            break
            
    dynamic_schema = get_pruned_schema(user_query)
    
    system_prompt = SystemMessage(
        content=(
            "You are an expert Enterprise Database & Supply Chain SQL Specialist.\n"
            "Relevant Database Schema:\n"
            f"{dynamic_schema}\n\n"
            "Instructions:\n"
            "1. Review the conversation history for context if the user's latest request refers to previous topics.\n"
            "2. Write an optimal SQLite SELECT query to answer the user's latest request.\n"
            "3. Put your SQL query inside a markdown code block like this: ```sql\nSELECT ...\n```\n"
            "4. Do NOT chat or explain yourself. Output the SQL query."
        )
    )
    
    # CONVERSATION MEMORY FILTER: 
    # Keep past Human/AI text dialogue (last 4 messages) for context, but exclude old raw ToolMessages.
    clean_history = []
    for msg in messages[:-1]:  # Exclude the very last message (handled separately)
        if isinstance(msg, (HumanMessage, AIMessage)) and not (hasattr(msg, "tool_calls") and msg.tool_calls):
            clean_history.append(msg)
            
    # Restrict window size to avoid token bloat and confusion (last 4 turns)
    clean_history = clean_history[-4:]
    
    chat_messages = [system_prompt] + clean_history + [messages[-1]]
    response = llm.invoke(chat_messages)
    content = response.content.strip()
    
    # 1. Try finding SQL inside a code block
    sql_match = re.search(r"```(?:sql|python)?\s*(SELECT[\s\S]*?)```", content, re.IGNORECASE)
    
    # 2. Fallback: Look for any standalone SELECT statement in the text
    if not sql_match:
        sql_match = re.search(r"(SELECT\s+[\s\S]*?)(?:;|\n\n|$)", content, re.IGNORECASE)
        
    if sql_match:
        raw_sql = sql_match.group(1).strip()
        sql_query = raw_sql.strip('`"\'')
        if not sql_query.endswith(";"):
            sql_query += ";"
            
        # Execute query using database tool function
        db_result = query_supply_chain_db.invoke({"query": sql_query, "user_question": user_query})
        
        # Feed result back for clean natural language synthesis, preserving clean history context
        followup_messages = [system_prompt] + clean_history + [
            messages[-1],
            AIMessage(content=content),
            ToolMessage(content=str(db_result), tool_call_id="manual_sql_exec")
        ]
        
        final_prompt = SystemMessage(content=f"Based on the database results above: {db_result}, write a clear, professional, natural language sentence answering the user's latest request. Do not include code blocks.")
        final_response = llm.invoke(followup_messages + [final_prompt])
        return {"messages": [final_response]}
        
    return {"messages": [response]}


# ==========================================
# 2. SUPPLIER RISK ANALYST WORKER
# ==========================================
def risk_worker_node(state):
    """Risk analyst worker with sliding conversational memory."""
    messages = state["messages"]
    
    user_query = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_query = msg.content
            break
            
    system_prompt = SystemMessage(
        content=(
            "You are an Enterprise Supplier Risk Analyst.\n"
            "Review the conversation history for context if needed, and write the target supplier name inside a code block like this: ```supplier Name_Here ```."
        )
    )
    
    clean_history = []
    for msg in messages[:-1]:
        if isinstance(msg, (HumanMessage, AIMessage)) and not (hasattr(msg, "tool_calls") and msg.tool_calls):
            clean_history.append(msg)
    clean_history = clean_history[-4:]
    
    chat_messages = [system_prompt] + clean_history + [messages[-1]]
    response = llm.invoke(chat_messages)
    content = response.content.strip()
    
    supp_match = re.search(r"```(?:supplier)?\s*(.*?)```", content, re.IGNORECASE)
    if not supp_match:
        supp_match = re.search(r"(?:for|supplier)\s+([A-Za-z\s]+)(?:\.|$)", content, re.IGNORECASE)
        
    if supp_match:
        supplier_name = supp_match.group(1).strip('`"\'')
        risk_result = analyze_supplier_risk_metrics.invoke({"supplier_name": supplier_name})
        
        followup_messages = [system_prompt] + clean_history + [
            messages[-1],
            AIMessage(content=content),
            ToolMessage(content=str(risk_result), tool_call_id="manual_risk_exec")
        ]
        
        final_prompt = SystemMessage(content=f"Write ONLY the final professional risk assessment answering the user's latest request based on these metrics: {risk_result}.")
        final_response = llm.invoke(followup_messages + [final_prompt])
        return {"messages": [final_response]}
        
    return {"messages": [response]}