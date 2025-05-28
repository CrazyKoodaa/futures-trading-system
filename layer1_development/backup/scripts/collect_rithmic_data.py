# collect_rithmic_data.py
"""
Command-line script to collect data from Rithmic
"""
import argparse
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from layer1_development.data_collection.rithmic_live_collector import main as collect_live_data
from layer1_development.data_collection.rithmic_historical_collector import main as collect_historical_data
from layer1_development.data_collection.rithmic_symbol_search import main as search_symbols

def main():
    parser = argparse.ArgumentParser(description='Collect data from Rithmic')
    parser.add_argument('action', choices=['live', 'historical', 'search'], 
                        help='Type of data collection to perform')
    
    args = parser.parse_args()
    
    if args.action == 'live':
        asyncio.run(collect_live_data())
    elif args.action == 'historical':
        asyncio.run(collect_historical_data())
    elif args.action == 'search':
        asyncio.run(search_symbols())

if __name__ == "__main__":
    main()