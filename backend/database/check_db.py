import sqlite3
import os

db_path = r"d:\FYP\Argus\backend\database\argus.db"
print(f"Checking DB at: {db_path}")
if not os.path.exists(db_path):
    print("  DB file not found!")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables: {tables}")

# If nodes table exists, let's see some nodes
if ('nodes',) in tables:
    cursor.execute("SELECT name, path FROM nodes LIMIT 5")
    print(f"Recent Nodes: {cursor.fetchall()}")
