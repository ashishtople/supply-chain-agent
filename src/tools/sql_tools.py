from langchain_core.tools import tool
from src.database import get_db_connection

# Master Schema Registry for Enterprise Pruning
SCHEMA_REGISTRY = {
    "suppliers": "suppliers(supplier_id, supplier_name, tier, country, avg_lead_time_days, rating)",
    "warehouses": "warehouses(warehouse_id, warehouse_name, city, capacity_sqft)",
    "product_categories": "product_categories(category_id, category_name, description)",
    "products": "products(product_id, sku, product_name, category_id [FK->product_categories], unit_price)",
    "inventory": "inventory(inventory_id, product_id [FK->products], warehouse_id [FK->warehouses], supplier_id [FK->suppliers], stock_quantity, reorder_level)",
    "purchase_orders": "purchase_orders(order_id, supplier_id [FK->suppliers], order_date, expected_delivery_date, status, total_amount)",
    "shipments": "shipments(shipment_id, order_id [FK->purchase_orders], dispatch_date, actual_delivery_date, shipping_cost, delay_days)"
}

def get_pruned_schema(query: str) -> str:
    """Intelligently select relevant table schemas based on user query keywords to save token context."""
    query_lower = query.lower()
    selected_schemas = []
    
    # Keyword mapping for schema pruning
    keyword_mapping = {
        "supplier": ["suppliers", "inventory", "purchase_orders"],
        "warehouse": ["warehouses", "inventory"],
        "stock": ["inventory", "products"],
        "sku": ["products", "inventory"],
        "price": ["products"],
        "order": ["purchase_orders", "suppliers", "shipments"],
        "shipment": ["shipments", "purchase_orders", "suppliers"],
        "delay": ["shipments", "suppliers", "purchase_orders"],
        "category": ["product_categories", "products"]
    }
    
    matched_tables = set(["suppliers", "inventory", "products"]) # Always include core tables as safe default
    for keyword, tables in keyword_mapping.items():
        if keyword in query_lower:
            matched_tables.update(tables)
            
    for tbl in matched_tables:
        if tbl in SCHEMA_REGISTRY:
            selected_schemas.append(f"- {SCHEMA_REGISTRY[tbl]}")
            
    return "\n".join(selected_schemas)

@tool
def query_supply_chain_db(query: str, user_question: str = "") -> str:
    """Execute a read-only SQL query against the enterprise supply chain SQLite database.
    
    Rules:
    - Use standard SQLite syntax (SELECT, JOIN, WHERE, GROUP BY, ORDER BY).
    - ONLY SELECT statements are permitted for security.
    """
    try:
        cleaned_query = query.strip()
        if not cleaned_query.upper().startswith("SELECT"):
            return "ERROR: Only SELECT queries are permitted for safety reasons."
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(cleaned_query)
        rows = cursor.fetchall()
        
        if not rows:
            return "No matching records found in the database."
            
        result_list = [dict(row) for row in rows]
        conn.close()
        return str(result_list)
        
    except Exception as e:
        return f"Database Execution Error: {str(e)}"