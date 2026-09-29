"""
Generate the Global Retail Sales dataset (10,000 transactions, 2022-2024).
"""
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

random.seed(42)
np.random.seed(42)

REGIONS = {
    "North America": ["United States", "Canada", "Mexico"],
    "Europe": ["Germany", "France", "United Kingdom", "Italy", "Spain"],
    "Asia Pacific": ["Japan", "China", "Australia", "India", "South Korea"],
    "Latin America": ["Brazil", "Argentina", "Colombia", "Chile"],
}

PRODUCTS = {
    "Electronics": {
        "Laptops": (800, 2500),
        "Smartphones": (400, 1200),
        "Tablets": (200, 800),
        "Accessories": (20, 150),
    },
    "Furniture": {
        "Office Chairs": (150, 800),
        "Desks": (200, 1200),
        "Storage": (80, 400),
        "Lighting": (30, 200),
    },
    "Office Supplies": {
        "Paper & Notebooks": (5, 50),
        "Pens & Markers": (3, 30),
        "Organizers": (10, 80),
        "Printers & Ink": (50, 300),
    },
    "Clothing": {
        "Formal Wear": (80, 400),
        "Casual Wear": (20, 150),
        "Sportswear": (30, 200),
        "Accessories": (10, 100),
    },
}

SEGMENTS = ["Consumer", "Corporate", "Small Business", "Government"]

SEGMENT_MULTIPLIERS = {
    "Consumer": 1.0,
    "Corporate": 2.5,
    "Small Business": 1.5,
    "Government": 3.0,
}

SEASONAL_MULTIPLIERS = {
    1: 0.8, 2: 0.75, 3: 0.9, 4: 0.95,
    5: 1.0, 6: 1.05, 7: 1.1, 8: 1.15,
    9: 1.1, 10: 1.2, 11: 1.4, 12: 1.5,
}

PROFIT_MARGINS = {
    "Electronics": (0.15, 0.30),
    "Furniture": (0.25, 0.45),
    "Office Supplies": (0.35, 0.55),
    "Clothing": (0.40, 0.65),
}

def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))

def generate_dataset(n=10000):
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2024, 12, 31)

    records = []
    for i in range(n):
        region = random.choice(list(REGIONS.keys()))
        country = random.choice(REGIONS[region])
        category = random.choice(list(PRODUCTS.keys()))
        subcategory = random.choice(list(PRODUCTS[category].keys()))
        price_range = PRODUCTS[category][subcategory]
        segment = random.choice(SEGMENTS)

        order_date = random_date(start_date, end_date)
        month = order_date.month
        year = order_date.year
        quarter = (month - 1) // 3 + 1

        base_price = random.uniform(*price_range)
        seg_mult = SEGMENT_MULTIPLIERS[segment]
        season_mult = SEASONAL_MULTIPLIERS[month]

        # Year over year growth trend
        year_mult = 1.0 + (year - 2022) * 0.12

        unit_price = round(base_price * seg_mult * 0.4, 2)
        quantity = max(1, int(np.random.exponential(2) * season_mult * year_mult))
        revenue = round(unit_price * quantity, 2)

        margin_range = PROFIT_MARGINS[category]
        profit_margin = random.uniform(*margin_range)
        cost = round(revenue * (1 - profit_margin), 2)
        profit = round(revenue - cost, 2)

        records.append({
            "order_id": f"ORD-{i+1:05d}",
            "order_date": order_date.strftime("%Y-%m-%d"),
            "year": year,
            "quarter": f"Q{quarter}",
            "month": month,
            "month_name": order_date.strftime("%B"),
            "region": region,
            "country": country,
            "category": category,
            "subcategory": subcategory,
            "customer_segment": segment,
            "quantity": quantity,
            "unit_price": unit_price,
            "revenue": revenue,
            "cost": cost,
            "profit": profit,
            "profit_margin": round(profit_margin * 100, 2),
        })

    df = pd.DataFrame(records)
    df = df.sort_values("order_date").reset_index(drop=True)
    return df

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    df = generate_dataset(10000)
    df.to_csv("data/global_retail_sales.csv", index=False)
    print(f"Dataset generated: {len(df)} records")
    print(df.describe())
