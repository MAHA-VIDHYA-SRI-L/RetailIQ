"""Deterministic Synthetic Data Generator for RetailIQ.

Generates realistic retail datasets:
- data/products.csv (40 products across 6 categories with INR prices)
- data/stores.csv (4 fictional retail stores across major Indian cities)
- data/sales.csv (120 days of historical sales with realistic demand, trends, and anomalies)
- data/inventory.csv (current inventory snapshot for 160 store-product pairs with deliberate stockout & overstock scenarios)
"""

import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

# Set fixed random seeds for deterministic reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 1. Product Catalog (40 products across 6 categories)
PRODUCTS: List[Dict[str, Any]] = [
    # Electronics (8)
    {"product_id": "PRD001", "product_name": "Wireless Optical Mouse", "category": "Electronics", "unit_price": 599.0, "reorder_level": 25, "tier": "fast"},
    {"product_id": "PRD002", "product_name": "Mechanical Gaming Keyboard", "category": "Electronics", "unit_price": 2899.0, "reorder_level": 15, "tier": "medium"},
    {"product_id": "PRD003", "product_name": "Bluetooth Soundbar 40W", "category": "Electronics", "unit_price": 3499.0, "reorder_level": 10, "tier": "medium"},
    {"product_id": "PRD004", "product_name": "10000mAh Fast Power Bank", "category": "Electronics", "unit_price": 1199.0, "reorder_level": 20, "tier": "fast"},
    {"product_id": "PRD005", "product_name": "Noise-Cancelling Wireless Earbuds", "category": "Electronics", "unit_price": 2299.0, "reorder_level": 15, "tier": "spike"},
    {"product_id": "PRD006", "product_name": "Smart Fitness Band with AMOLED", "category": "Electronics", "unit_price": 1799.0, "reorder_level": 15, "tier": "medium"},
    {"product_id": "PRD007", "product_name": "FHD USB Streaming Webcam 1080p", "category": "Electronics", "unit_price": 1999.0, "reorder_level": 12, "tier": "drop"},
    {"product_id": "PRD008", "product_name": "7-in-1 USB-C Hub Adapter", "category": "Electronics", "unit_price": 1499.0, "reorder_level": 15, "tier": "medium"},

    # Accessories (7)
    {"product_id": "PRD009", "product_name": "Braided Nylon USB-C Cable (2m)", "category": "Accessories", "unit_price": 299.0, "reorder_level": 40, "tier": "fast"},
    {"product_id": "PRD010", "product_name": "Ergonomic Aluminum Laptop Stand", "category": "Accessories", "unit_price": 1299.0, "reorder_level": 15, "tier": "store_special"},
    {"product_id": "PRD011", "product_name": "Waterproof Laptop Backpack 15.6\"", "category": "Accessories", "unit_price": 1599.0, "reorder_level": 15, "tier": "medium"},
    {"product_id": "PRD012", "product_name": "Microfiber Cleaning Cloth (Pack of 5)", "category": "Accessories", "unit_price": 199.0, "reorder_level": 30, "tier": "medium"},
    {"product_id": "PRD013", "product_name": "Tempered Glass Screen Protector", "category": "Accessories", "unit_price": 249.0, "reorder_level": 35, "tier": "medium"},
    {"product_id": "PRD014", "product_name": "Wireless Car Charger Mount", "category": "Accessories", "unit_price": 899.0, "reorder_level": 12, "tier": "slow"},
    {"product_id": "PRD015", "product_name": "Cable Management Box Organizer", "category": "Accessories", "unit_price": 449.0, "reorder_level": 20, "tier": "medium"},

    # Home (7)
    {"product_id": "PRD016", "product_name": "Smart LED Desk Lamp with Dimmer", "category": "Home", "unit_price": 1199.0, "reorder_level": 15, "tier": "medium"},
    {"product_id": "PRD017", "product_name": "Ceramic Coffee Mug Set (Set of 4)", "category": "Home", "unit_price": 649.0, "reorder_level": 20, "tier": "medium"},
    {"product_id": "PRD018", "product_name": "Stainless Steel Insulated Flask 1L", "category": "Home", "unit_price": 899.0, "reorder_level": 25, "tier": "spike"},
    {"product_id": "PRD019", "product_name": "Ultrasonic Aroma Diffuser & Humidifier", "category": "Home", "unit_price": 1399.0, "reorder_level": 10, "tier": "slow"},
    {"product_id": "PRD020", "product_name": "Cotton Bed Sheet Set (Queen Size)", "category": "Home", "unit_price": 1499.0, "reorder_level": 12, "tier": "medium"},
    {"product_id": "PRD021", "product_name": "Non-Stick Induction Frying Pan 24cm", "category": "Home", "unit_price": 1099.0, "reorder_level": 15, "tier": "medium"},
    {"product_id": "PRD022", "product_name": "Bamboo Fiber Cutlery Tray Organizer", "category": "Home", "unit_price": 599.0, "reorder_level": 15, "tier": "slow"},

    # Personal Care (6)
    {"product_id": "PRD023", "product_name": "Rechargeable Sonic Electric Toothbrush", "category": "Personal Care", "unit_price": 1299.0, "reorder_level": 15, "tier": "medium"},
    {"product_id": "PRD024", "product_name": "Cordless Men's Beard Trimmer", "category": "Personal Care", "unit_price": 1499.0, "reorder_level": 15, "tier": "medium"},
    {"product_id": "PRD025", "product_name": "Ionic Hair Dryer 1600W", "category": "Personal Care", "unit_price": 1899.0, "reorder_level": 12, "tier": "medium"},
    {"product_id": "PRD026", "product_name": "Organic Aloe Vera Soothing Gel 250ml", "category": "Personal Care", "unit_price": 299.0, "reorder_level": 30, "tier": "fast"},
    {"product_id": "PRD027", "product_name": "Activated Charcoal Toothpaste 150g", "category": "Personal Care", "unit_price": 179.0, "reorder_level": 35, "tier": "medium"},
    {"product_id": "PRD028", "product_name": "SPF 50 PA+++ Mineral Sunscreen Lotion", "category": "Personal Care", "unit_price": 499.0, "reorder_level": 25, "tier": "drop"},

    # Office (6)
    {"product_id": "PRD029", "product_name": "Hardcover Dot Grid Journal Notebook A5", "category": "Office", "unit_price": 349.0, "reorder_level": 30, "tier": "medium"},
    {"product_id": "PRD030", "product_name": "Gel Ink Rollerball Pens (Pack of 10)", "category": "Office", "unit_price": 199.0, "reorder_level": 40, "tier": "fast"},
    {"product_id": "PRD031", "product_name": "Memory Foam Ergonomic Lumbar Cushion", "category": "Office", "unit_price": 999.0, "reorder_level": 15, "tier": "medium"},
    {"product_id": "PRD032", "product_name": "Desktop Metal Mesh File Tray 3-Tier", "category": "Office", "unit_price": 699.0, "reorder_level": 15, "tier": "slow"},
    {"product_id": "PRD033", "product_name": "Wireless Laser Presentation Remote Clicker", "category": "Office", "unit_price": 849.0, "reorder_level": 10, "tier": "slow"},
    {"product_id": "PRD034", "product_name": "Ergonomic Gel Keyboard Wrist Rest Pad", "category": "Office", "unit_price": 399.0, "reorder_level": 20, "tier": "medium"},

    # Grocery (6)
    {"product_id": "PRD035", "product_name": "Single Origin Arabica Whole Coffee Beans 250g", "category": "Grocery", "unit_price": 449.0, "reorder_level": 25, "tier": "store_special"},
    {"product_id": "PRD036", "product_name": "Masala Chai Blend CTC Premium Tea 500g", "category": "Grocery", "unit_price": 329.0, "reorder_level": 35, "tier": "fast"},
    {"product_id": "PRD037", "product_name": "Cold-Pressed Virgin Coconut Oil 500ml", "category": "Grocery", "unit_price": 379.0, "reorder_level": 25, "tier": "medium"},
    {"product_id": "PRD038", "product_name": "Raw Multifloral Organic Honey 500g", "category": "Grocery", "unit_price": 429.0, "reorder_level": 20, "tier": "medium"},
    {"product_id": "PRD039", "product_name": "Roasted Salted California Almonds 200g", "category": "Grocery", "unit_price": 299.0, "reorder_level": 30, "tier": "fast"},
    {"product_id": "PRD040", "product_name": "Whole Grain Rolled Oats 1kg", "category": "Grocery", "unit_price": 249.0, "reorder_level": 30, "tier": "fast"},
]

# 2. Stores (4 fictional stores across major Indian cities)
STORES: List[Dict[str, str]] = [
    {"store_id": "STR001", "store_name": "RetailIQ Prime - Indiranagar", "city": "Bengaluru"},
    {"store_id": "STR002", "store_name": "RetailIQ Metro - Bandra", "city": "Mumbai"},
    {"store_id": "STR003", "store_name": "RetailIQ Central - Connaught Place", "city": "Delhi"},
    {"store_id": "STR004", "store_name": "RetailIQ Hub - Hitec City", "city": "Hyderabad"},
]


def generate_datasets() -> None:
    """Generate products.csv, stores.csv, sales.csv, and inventory.csv."""
    # Write products.csv
    products_clean = [
        {
            "product_id": p["product_id"],
            "product_name": p["product_name"],
            "category": p["category"],
            "unit_price": p["unit_price"],
            "reorder_level": p["reorder_level"],
        }
        for p in PRODUCTS
    ]
    df_products = pd.DataFrame(products_clean)
    products_path = DATA_DIR / "products.csv"
    df_products.to_csv(products_path, index=False)
    print(f"Generated {products_path} ({len(df_products)} records)")

    # Write stores.csv
    df_stores = pd.DataFrame(STORES)
    stores_path = DATA_DIR / "stores.csv"
    df_stores.to_csv(stores_path, index=False)
    print(f"Generated {stores_path} ({len(df_stores)} records)")

    # 3. Generate 120 days of sales
    # Date range: 2026-05-08 to 2026-09-04 (120 days)
    start_date = date(2026, 5, 8)
    num_days = 120
    sales_records = []
    sale_counter = 1

    # Track sales per (store_id, product_id) to calculate realistic average daily sales
    store_product_sales: Dict[tuple, List[int]] = {
        (s["store_id"], p["product_id"]): []
        for s in STORES
        for p in PRODUCTS
    }

    # Store baseline multipliers
    store_multipliers = {
        "STR001": 1.15,  # Bengaluru
        "STR002": 1.25,  # Mumbai (high volume)
        "STR003": 1.05,  # Delhi
        "STR004": 1.10,  # Hyderabad
    }

    for day_idx in range(num_days):
        current_day = start_date + timedelta(days=day_idx)
        is_weekend = current_day.weekday() in (5, 6)
        weekend_boost = 1.25 if is_weekend else 1.0

        for store in STORES:
            s_id = store["store_id"]
            s_mult = store_multipliers[s_id] * weekend_boost

            for prod in PRODUCTS:
                p_id = prod["product_id"]
                tier = prod["tier"]
                category = prod["category"]
                unit_price = prod["unit_price"]

                # Determine base chance and base quantity range
                if tier == "fast":
                    prob = 0.85
                    qty_min, qty_max = 2, 7
                elif tier == "medium":
                    prob = 0.55
                    qty_min, qty_max = 1, 4
                elif tier == "slow":
                    prob = 0.22
                    qty_min, qty_max = 1, 2
                elif tier == "spike":
                    # Recent spike in last 18 days (days 102..119)
                    if day_idx >= 102:
                        prob = 0.95
                        qty_min, qty_max = 6, 12  # Major spike!
                    else:
                        prob = 0.50
                        qty_min, qty_max = 1, 3  # Normal baseline
                elif tier == "drop":
                    # Recent drop in last 25 days (days 95..119)
                    if day_idx >= 95:
                        prob = 0.15
                        qty_min, qty_max = 1, 1  # Noticeable drop!
                    else:
                        prob = 0.70
                        qty_min, qty_max = 2, 5  # Healthy baseline
                elif tier == "store_special":
                    # PRD010 (Laptop Stand) or PRD035 (Arabica Coffee) perform heavily in STR001 (Bengaluru)
                    if s_id == "STR001":
                        prob = 0.90
                        qty_min, qty_max = 4, 8
                    else:
                        prob = 0.30
                        qty_min, qty_max = 1, 2
                else:
                    prob = 0.5
                    qty_min, qty_max = 1, 3

                # Store-category affinities
                if s_id == "STR001" and category == "Electronics":
                    prob = min(0.95, prob * 1.15)
                elif s_id == "STR002" and category == "Accessories":
                    prob = min(0.95, prob * 1.15)
                elif s_id == "STR003" and category == "Home":
                    prob = min(0.95, prob * 1.10)

                # Random roll to see if a sale occurred on this day for this product & store
                if random.random() < prob:
                    # Quantity with integer rounding
                    raw_qty = random.randint(qty_min, qty_max)
                    qty = max(1, int(round(raw_qty * s_mult / 1.1)))
                    revenue = round(qty * unit_price, 2)

                    sales_records.append({
                        "sale_id": f"SAL{sale_counter:06d}",
                        "date": current_day.isoformat(),
                        "store_id": s_id,
                        "product_id": p_id,
                        "quantity": qty,
                        "unit_price": unit_price,
                        "revenue": revenue,
                    })
                    sale_counter += 1
                    store_product_sales[(s_id, p_id)].append(qty)
                else:
                    store_product_sales[(s_id, p_id)].append(0)

    df_sales = pd.DataFrame(sales_records)
    sales_path = DATA_DIR / "sales.csv"
    df_sales.to_csv(sales_path, index=False)
    print(f"Generated {sales_path} ({len(df_sales)} records, from {start_date} to {start_date + timedelta(days=num_days-1)})")

    # 4. Generate inventory.csv snapshot
    # Columns: store_id, product_id, current_stock, reorder_level
    # We calibrate inventory against average daily sales over the 120 days:
    inventory_records = []

    for store in STORES:
        s_id = store["store_id"]
        for prod in PRODUCTS:
            p_id = prod["product_id"]
            reorder_lvl = prod["reorder_level"]
            sales_history = store_product_sales[(s_id, p_id)]
            avg_daily_sales = sum(sales_history) / num_days if num_days > 0 else 1.0

            # Default healthy stock: roughly 14 to 28 days of average daily sales
            base_stock = max(int(reorder_lvl * 1.2), int(avg_daily_sales * random.uniform(14, 25)))

            # Deliberate scenarios:
            # A) Stock-out risk (at least 3 store/product combos with < 3.5 days coverage)
            if (s_id == "STR001" and p_id == "PRD009"):  # USB-C Cable in Bengaluru: high demand (~5/day), only 12 in stock
                base_stock = 12
            elif (s_id == "STR002" and p_id == "PRD026"):  # Aloe Vera Gel in Mumbai: high demand (~5/day), only 14 in stock
                base_stock = 14
            elif (s_id == "STR003" and p_id == "PRD036"):  # Masala Chai in Delhi: high demand (~6/day), only 15 in stock
                base_stock = 15
            elif (s_id == "STR004" and p_id == "PRD004"):  # Power Bank in Hyderabad: demand (~4/day), only 10 in stock
                base_stock = 10

            # B) Overstock (at least 3 store/product combos with huge coverage > 100 days)
            elif (s_id == "STR003" and p_id == "PRD014"):  # Car Mount in Delhi: slow moving (~0.3/day), 160 stock
                base_stock = 160
            elif (s_id == "STR001" and p_id == "PRD019"):  # Aroma Diffuser in Bengaluru: slow moving (~0.25/day), 125 stock
                base_stock = 125
            elif (s_id == "STR004" and p_id == "PRD032"):  # Mesh File Tray in Hyderabad: slow moving (~0.3/day), 140 stock
                base_stock = 140
            elif (s_id == "STR002" and p_id == "PRD022"):  # Cutlery Tray in Mumbai: slow moving (~0.3/day), 110 stock
                base_stock = 110

            inventory_records.append({
                "store_id": s_id,
                "product_id": p_id,
                "current_stock": int(base_stock),
                "reorder_level": int(reorder_lvl),
            })

    df_inventory = pd.DataFrame(inventory_records)
    inventory_path = DATA_DIR / "inventory.csv"
    df_inventory.to_csv(inventory_path, index=False)
    print(f"Generated {inventory_path} ({len(df_inventory)} records, exactly {len(STORES)} x {len(PRODUCTS)})")


if __name__ == "__main__":
    generate_datasets()
