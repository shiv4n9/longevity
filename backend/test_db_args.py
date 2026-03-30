import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/longevity"

async def test_conn(name, connect_args):
    try:
        engine = create_async_engine(DATABASE_URL, connect_args=connect_args)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"{name} SUCCESS:", result.scalar())
        await engine.dispose()
    except Exception as e:
        print(f"{name} ERROR:", str(e))

async def main():
    await test_conn("With SSL=False", {"ssl": False, "command_timeout": 60})
    await test_conn("Without SSL arg", {"command_timeout": 60})
    await test_conn("Just empty", {})

asyncio.run(main())
