import sqlite3
from src.config import settings

def get_db_connection():
    """Create and return a thread-safe connection to the SQLite database."""
    conn = sqlite3.connect(settings.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the 7-table normalized enterprise schema."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Enable Foreign Key constraints in SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Suppliers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_name TEXT UNIQUE NOT NULL,
        tier TEXT,
        country TEXT,
        avg_lead_time_days INTEGER,
        rating REAL
    )
    """)

    # 2. Warehouses Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS warehouses (
        warehouse_id INTEGER PRIMARY KEY AUTOINCREMENT,
        warehouse_name TEXT NOT NULL,
        city TEXT,
        capacity_sqft INTEGER
    )
    """)

    # 3. Product Categories Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product_categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT NOT NULL,
        description TEXT
    )
    """)

    # 4. Products Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        product_name TEXT NOT NULL,
        category_id INTEGER,
        unit_price REAL,
        FOREIGN KEY (category_id) REFERENCES product_categories (category_id)
    )
    """)

    # 5. Inventory Table (Junction of Product, Warehouse, Supplier)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        warehouse_id INTEGER,
        supplier_id INTEGER,
        stock_quantity INTEGER,
        reorder_level INTEGER,
        FOREIGN KEY (product_id) REFERENCES products (product_id),
        FOREIGN KEY (warehouse_id) REFERENCES warehouses (warehouse_id),
        FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id)
    )
    """)

    # 6. Purchase Orders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER,
        order_date TEXT,
        expected_delivery_date TEXT,
        status TEXT,
        total_amount REAL,
        FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id)
    )
    """)

    # 7. Shipments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shipments (
        shipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        dispatch_date TEXT,
        actual_delivery_date TEXT,
        shipping_cost REAL,
        delay_days INTEGER,
        FOREIGN KEY (order_id) REFERENCES purchase_orders (order_id)
    )
    """)

    conn.commit()
    conn.close()
    print("✅ 7-Table Enterprise Schema created successfully.")

def seed_db():
    """Seed rich enterprise sample data for testing complex joins & aggregations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM suppliers")
    if cursor.fetchone()[0] == 0:
        # Suppliers
        cursor.executemany("INSERT INTO suppliers (supplier_name, tier, country, avg_lead_time_days, rating) VALUES (?, ?, ?, ?, ?)", [
            ("Alpha Corp", "Tier 1", "India", 5, 4.8),
            ("Beta Logistics", "Tier 2", "India", 12, 3.2),
            ("Gamma Supply", "Tier 1", "Germany", 7, 4.6)
        ])

        # Warehouses
        cursor.executemany("INSERT INTO warehouses (warehouse_name, city, capacity_sqft) VALUES (?, ?, ?)", [
            ("Pune Central Hub", "Pune", 50000),
            ("Mumbai Port Hub", "Mumbai", 80000),
            ("Delhi North Hub", "Delhi", 65000)
        ])

        # Categories
        cursor.executemany("INSERT INTO product_categories (category_name, description) VALUES (?, ?)", [
            ("Electronics", "Microcontrollers, sensors, and actuators"),
            ("Mechanical", "Valves, bearings, and structural steel")
        ])

        # Products
        cursor.executemany("INSERT INTO products (sku, product_name, category_id, unit_price) VALUES (?, ?, ?, ?)", [
            ("SKU123", "Industrial IoT Sensor", 1, 45.50),
            ("SKU456", "High-Pressure Valve", 2, 120.00),
            ("SKU789", "Precision Ball Bearing", 2, 15.75)
        ])

        # Inventory
        cursor.executemany("INSERT INTO inventory (product_id, warehouse_id, supplier_id, stock_quantity, reorder_level) VALUES (?, ?, ?, ?, ?)", [
            (1, 1, 1, 120, 20), # SKU123 at Pune by Alpha
            (1, 3, 2, 2, 25),   # SKU123 at Delhi by Beta
            (2, 2, 1, 0, 10),   # SKU456 at Mumbai by Alpha
            (2, 3, 2, 80, 15),  # SKU456 at Delhi by Beta
            (3, 1, 3, 300, 50)  # SKU789 at Pune by Gamma
        ])

        # Purchase Orders
        cursor.executemany("INSERT INTO purchase_orders (supplier_id, order_date, expected_delivery_date, status, total_amount) VALUES (?, ?, ?, ?, ?)", [
            (1, "2026-05-01", "2026-05-06", "Delivered", 5460.00),
            (2, "2026-05-03", "2026-05-15", "Delayed", 960.00),
            (3, "2026-05-10", "2026-05-17", "In Transit", 12600.00)
        ])

        # Shipments & Delays
        cursor.executemany("INSERT INTO shipments (order_id, dispatch_date, actual_delivery_date, shipping_cost, delay_days) VALUES (?, ?, ?, ?, ?)", [
            (1, "2026-05-02", "2026-05-06", 450.00, 0),
            (2, "2026-05-04", "2026-05-18", 320.00, 3),
            (3, "2026-05-11", "2026-05-18", 1200.00, 0)
        ])

        conn.commit()
        print("✅ Enterprise seed data populated successfully.")
    
    conn.close()

if __name__ == "__main__":
    init_db()
    seed_db()