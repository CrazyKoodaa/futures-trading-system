# test_db_connection.py
import asyncio
import asyncpg
import os

async def test_connection():
    """Test connection to the PostgreSQL database"""
    print("Testing database connection...")
    
    # Connection parameters
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = int(os.getenv('POSTGRES_PORT', '5432'))
    database = os.getenv('POSTGRES_DB', 'trading_db')
    user = os.getenv('POSTGRES_USER', 'trading_user')
    password = os.getenv('POSTGRES_PASSWORD', 'myData4Tr4ding42!')
    
    print(f"Connecting to: {host}:{port}/{database} as {user}")
    
    try:
        # Connect to the database
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        # Test query
        version = await conn.fetchval("SELECT version()")
        
        print(f"[SUCCESS] Connected to PostgreSQL!")
        print(f"PostgreSQL version: {version}")
        
        # Close the connection
        await conn.close()
        
        return True
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())