"""
Creates a sample e-commerce SQLite database with realistic, randomized data.
Run this once to generate data/ecommerce.db before starting the agent.
"""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "ecommerce.db"

random.seed(42)

CATEGORIES = ["Electronics", "Home & Kitchen", "Sports", "Books", "Beauty", "Toys"]
PRODUCT_NAMES = {
    "Electronics": ["Wireless Earbuds", "Bluetooth Speaker", "USB-C Hub", "Smart Watch", "Laptop Stand"],
    "Home & Kitchen": ["Air Fryer", "Coffee Maker", "Blender", "Cutlery Set", "Non-stick Pan"],
    "Sports": ["Yoga Mat", "Resistance Bands", "Water Bottle", "Running Shoes", "Dumbbell Set"],
    "Books": ["Fiction Novel", "Cookbook", "Self-Help Guide", "Biography", "Sci-Fi Anthology"],
    "Beauty": ["Face Serum", "Hair Dryer", "Makeup Kit", "Sunscreen", "Shampoo Set"],
    "Toys": ["Building Blocks", "RC Car", "Puzzle Set", "Board Game", "Action Figure"],
}
CITIES = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Delhi", "Mumbai", "Bengaluru", "London", "Toronto"]
STATUSES = ["completed", "completed", "completed", "completed", "cancelled", "refunded"]


def build_database():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            city TEXT NOT NULL,
            signup_date TEXT NOT NULL
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            cost REAL NOT NULL
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE order_items (
            order_item_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        """
    )

    # Customers
    customers = []
    start = datetime(2024, 1, 1)
    for i in range(1, 201):
        signup = start + timedelta(days=random.randint(0, 550))
        customers.append((i, f"Customer {i}", f"customer{i}@example.com", random.choice(CITIES), signup.strftime("%Y-%m-%d")))
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", customers)

    # Products
    products = []
    pid = 1
    for category, names in PRODUCT_NAMES.items():
        for name in names:
            price = round(random.uniform(10, 300), 2)
            cost = round(price * random.uniform(0.4, 0.7), 2)
            products.append((pid, name, category, price, cost))
            pid += 1
    cur.executemany("INSERT INTO products VALUES (?,?,?,?,?)", products)

    # Orders + order_items
    orders = []
    order_items = []
    order_id = 1
    item_id = 1
    for _ in range(1500):
        customer_id = random.randint(1, 200)
        order_date = start + timedelta(days=random.randint(0, 560))
        status = random.choice(STATUSES)
        orders.append((order_id, customer_id, order_date.strftime("%Y-%m-%d"), status))

        for _ in range(random.randint(1, 4)):
            product = random.choice(products)
            quantity = random.randint(1, 3)
            order_items.append((item_id, order_id, product[0], quantity, product[3]))
            item_id += 1

        order_id += 1

    cur.executemany("INSERT INTO orders VALUES (?,?,?,?)", orders)
    cur.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", order_items)

    conn.commit()
    conn.close()
    print(f"Database created at {DB_PATH} with {len(customers)} customers, "
          f"{len(products)} products, {len(orders)} orders, {len(order_items)} order items.")


if __name__ == "__main__":
    build_database()
