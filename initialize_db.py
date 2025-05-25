# initialize_db.py
import asyncio
import os
import sys
import logging
from shared.database.connection import test_database_setup

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def initialize_database():
    """Initialize the database using the admin user"""
    # Set environment variable to use admin credentials
    os.environ['DB_INIT_MODE'] = 'True'
    
    try:
        logger.info("Initializing database with admin privileges...")
        success = await test_database_setup()
        
        if success:
            logger.info("[SUCCESS] Database initialized successfully!")
            return True
        else:
            logger.error("[ERROR] Database initialization failed!")
            return False
    finally:
        # Reset environment variable
        os.environ['DB_INIT_MODE'] = 'False'

if __name__ == "__main__":
    success = asyncio.run(initialize_database())
    if not success:
        sys.exit(1)