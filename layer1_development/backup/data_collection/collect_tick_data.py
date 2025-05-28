# layer1_development/collect_tick_data.py
import asyncio
from config.chicago_gateway_config import config
from data_collection.async_rithmic_tick_collector import AsyncRithmicTickCollector

async def collect_second_data():
    async with AsyncRithmicTickCollector(config) as collector:
        # Get current NQ/ES contracts
        contracts = collector.generate_current_contracts(['NQ', 'ES'])
        print(f"Collecting: {contracts}")
        
        # Start real-time collection
        await collector.start_tick_collection(contracts)
        
        # Collect for desired duration
        print("🔄 Collecting second-based data...")
        await asyncio.sleep(3600)  # 1 hour
        
        # Stop and get stats
        await collector.stop_tick_collection()
        stats = collector.get_stats()
        print(f"📊 Collected {stats['ticks_received']} ticks, {stats['seconds_aggregated']} seconds")

if __name__ == "__main__":
    asyncio.run(collect_second_data())