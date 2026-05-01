import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="argus_db",
    user="argus",
    password="8888"
)
cursor = conn.cursor()

print("Cleaning up Kiro.exe false positive incidents...")

# Count incidents to be cleaned
cursor.execute("""
    SELECT COUNT(*) FROM incidents i
    WHERE EXISTS (
        SELECT 1 FROM edges e 
        JOIN nodes n1 ON e.source_id = n1.id 
        JOIN nodes n2 ON e.target_id = n2.id 
        WHERE e.session_id = i.session_id 
        AND n1.name LIKE '%Kiro%' 
        AND (n2.name LIKE '%cmd%' OR n2.name LIKE '%powershell%')
    )
""")
count = cursor.fetchone()[0]
print(f"Found {count} Kiro.exe incidents to clean up")

if count > 0:
    choice = input("Delete them? (y/n): ")
    if choice.lower() == 'y':
        # Delete incidents
        cursor.execute("""
            DELETE FROM incidents 
            WHERE id IN (
                SELECT i.id FROM incidents i
                WHERE EXISTS (
                    SELECT 1 FROM edges e 
                    JOIN nodes n1 ON e.source_id = n1.id 
                    JOIN nodes n2 ON e.target_id = n2.id 
                    WHERE e.session_id = i.session_id 
                    AND n1.name LIKE '%Kiro%' 
                    AND (n2.name LIKE '%cmd%' OR n2.name LIKE '%powershell%')
                )
            )
        """)
        deleted = cursor.rowcount
        
        # Update edges to BENIGN
        cursor.execute("""
            UPDATE edges 
            SET final_severity = 'BENIGN', anomaly_score = 0.05
            WHERE id IN (
                SELECT e.id FROM edges e
                JOIN nodes n1 ON e.source_id = n1.id 
                JOIN nodes n2 ON e.target_id = n2.id 
                WHERE n1.name LIKE '%Kiro%' 
                AND (n2.name LIKE '%cmd%' OR n2.name LIKE '%powershell%')
            )
        """)
        updated_edges = cursor.rowcount
        
        conn.commit()
        print(f"✅ Deleted {deleted} incidents")
        print(f"✅ Updated {updated_edges} edges to BENIGN")
    else:
        print("Cancelled")
else:
    print("No Kiro.exe incidents found")

cursor.close()
conn.close()
