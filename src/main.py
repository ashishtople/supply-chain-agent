from langchain_core.messages import HumanMessage
from src.agents.supervisor import compiled_graph

def run_test():
    print("🚀 Initializing Enterprise Supply Chain Multi-Agent System...\n")
    
    test_queries = [
        "Which supplier offers SKU123 at the lowest unit price, and what warehouse is it stored in?",
        "Show me all purchase orders that are currently delayed and their associated supplier names.",
        "What is the total stock quantity of SKU123 across all warehouses?"
    ]
    
    for query in test_queries:
        print(f"👤 User Query: {query}")
        print("-" * 60)
        
        inputs = {"messages": [HumanMessage(content=query)]}
        
        # Stream events through the compiled graph
        final_response = ""
        for event in compiled_graph.stream(inputs, stream_mode="values"):
            latest_message = event["messages"][-1]
            if hasattr(latest_message, "content") and latest_message.content:
                final_response = latest_message.content
                
        print(f"🤖 Agent Response:\n{final_response}\n")
        print("=" * 60 + "\n")

if __name__ == "__main__":
    run_test()