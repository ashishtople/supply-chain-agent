from langchain_core.tools import tool
from src.database import get_db_connection

@tool
def analyze_supplier_risk_metrics(supplier_name: str) -> str:
    """Analyze supplier risk metrics including average lead times, delivery delay days, tier, and ratings.
    
    Args:
        supplier_name: The name of the supplier (e.g., 'Alpha Corp', 'Beta Logistics', 'Gamma Supply').
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                s.supplier_name,
                s.tier,
                s.country,
                s.avg_lead_time_days,
                s.rating,
                COUNT(sh.shipment_id) as total_shipments,
                AVG(sh.delay_days) as avg_delay_days
            FROM suppliers s
            LEFT JOIN purchase_orders po ON s.supplier_id = po.supplier_id
            LEFT JOIN shipments sh ON po.order_id = sh.order_id
            WHERE s.supplier_name LIKE ?
            GROUP BY s.supplier_id
        """, (f"%{supplier_name}%",))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return f"No supplier risk records found matching name '{supplier_name}'."
            
        result = dict(row)
        
        # Calculate a deterministic risk heuristic
        avg_delay = result.get("avg_delay_days") or 0.0
        rating = result.get("rating") or 3.0
        
        risk_level = "LOW"
        if avg_delay > 2 or rating < 4.0:
            risk_level = "MEDIUM"
        if avg_delay > 5 or rating < 3.5:
            risk_level = "HIGH"
            
        result["calculated_risk_tier"] = risk_level
        return str(result)
        
    except Exception as e:
        return f"Supplier Risk Analysis Error: {str(e)}"