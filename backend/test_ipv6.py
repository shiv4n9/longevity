import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

urls = [
    "postgresql+asyncpg://postgres:postgres@localhost:5433/longevity",
    "postgresql+asyncpg://postgres:postgres@[::1]:5433/longevity"
]

async def main():
    for url in urls:
        print(f"Testing {url}")
        try:
            engine = create_async_engine(url, connect_args={"ssl": False})
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                print("SUCCESS:", result.scalar())
            await engine.dispose()
        except Exception as e:
            print("ERROR:", str(e))

asyncio.run(main())
