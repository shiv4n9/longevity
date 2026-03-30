from sqlalchemy import create_engine
from sqlalchemy import text

DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5433/longevity"

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("SYNC SUCCESS:", result.scalar())
except Exception as e:
    print("SYNC ERROR:", str(e))
