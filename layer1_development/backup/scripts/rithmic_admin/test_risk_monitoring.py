"""
Test script for risk monitoring functionality
"""

import asyncio
import sys
import os

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from layer1_development.scripts.rithmic_admin.risk_monitoring import RiskMonitor, RiskMonitoringUI, run_risk_monitoring

async def main():
    """Test the risk monitoring functionality"""
    print("Testing Risk Monitoring...")
    
    try:
        # Run risk monitoring with no Rithmic client (demo mode)
        await run_risk_monitoring()
    except KeyboardInterrupt:
        print("Test interrupted by user")
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())