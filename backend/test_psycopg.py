import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:5433/longevity"

async def test_conn():
    try:
        engine = create_async_engine(DATABASE_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("PSYCOPG SUCCESS:", result.scalar())
        await engine.dispose()
    except Exception as e:
        print("PSYCOPG ERROR:", str(e))

asyncio.run(test_conn())
