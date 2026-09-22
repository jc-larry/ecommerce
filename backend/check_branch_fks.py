from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
tables_query = text("""
    SELECT tc.table_name, kcu.column_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name='branches';
""")
rows = db.execute(tables_query).fetchall()
print("Tablas con Foreign Key a branches:")
for r in rows:
    print(f"  {r[0]}.{r[1]}")
