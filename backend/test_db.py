import asyncio
from app.core.database import engine
from sqlalchemy import text

async def main():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("DB SUCCESS:", result.scalar())
    except Exception as e:
        print("DB ERROR:", str(e))

asyncio.run(main())
