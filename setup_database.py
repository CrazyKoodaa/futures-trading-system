# setup_database.py
import asyncio
from shared.database.connection import test_database_setup

async def setup():
    success = await test_database_setup()
    if success:
        print("[SUCCESS] Database ready for tick collection!")
    else:
        print("[ERROR] Database setup failed")

asyncio.run(setup())