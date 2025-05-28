"""
Risk Monitoring Module for Enhanced Rithmic Admin Tool

This module provides real-time risk monitoring functionality for futures trading accounts.
It connects to the Rithmic API to fetch live position, P&L, and margin data.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import random  # For demo data generation only

# Rich library for modern UI components
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.layout import Layout
    from rich.text import Text
    from rich.align import Align
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import Rithmic client
from async_rithmic import RithmicClient

# Setup logging
logger = logging.getLogger("rithmic_admin.risk")

class AccountRiskData:
    """Data class for account risk information"""
    
    def __init__(self, account_id: str):
        self.account_id = account_id
        self.positions: Dict[str, int] = {}  # Symbol -> Position size
        self.pnl: float = 0.0
        self.margin_used: float = 0.0
        self.margin_available: float = 0.0
        self.risk_level: str = "Low"
        self.last_update: datetime = datetime.now()
        
    def update_position(self, symbol: str, position: int):
        """Update position for a specific symbol"""
        self.positions[symbol] = position
        self.last_update = datetime.now()
        
    def update_pnl(self, pnl: float):
        """Update P&L value"""
        self.pnl = pnl
        self._calculate_risk_level()
        self.last_update = datetime.now()
        
    def update_margin(self, used: float, available: float):
        """Update margin information"""
        self.margin_used = used
        self.margin_available = available
        self._calculate_risk_level()
        self.last_update = datetime.now()
        
    def _calculate_risk_level(self):
        """Calculate risk level based on P&L and margin"""
        # Simple risk calculation logic
        if self.margin_available <= 0:
            self.risk_level = "Critical"
        elif self.pnl < -5000 or self.margin_used > 0.9 * (self.margin_used + self.margin_available):
            self.risk_level = "High"
        elif self.pnl < 0 or self.margin_used > 0.7 * (self.margin_used + self.margin_available):
            self.risk_level = "Medium"
        else:
            self.risk_level = "Low"
            
    def get_total_position(self) -> int:
        """Get total position across all symbols"""
        return sum(self.positions.values())
        
    def get_risk_color(self) -> str:
        """Get color code for risk level"""
        if self.risk_level == "Critical":
            return "bold red"
        elif self.risk_level == "High":
            return "red"
        elif self.risk_level == "Medium":
            return "yellow"
        else:
            return "green"


class RiskMonitor:
    """Risk monitoring service for Rithmic accounts"""
    
    def __init__(self, rithmic_client: Optional[RithmicClient] = None):
        self.rithmic_client = rithmic_client
        self.accounts: Dict[str, AccountRiskData] = {}
        self.running = False
        self.update_interval = 2.0  # seconds
        self.demo_mode = True if rithmic_client is None else False
        
    def add_account(self, account_id: str):
        """Add an account to monitor"""
        if account_id not in self.accounts:
            self.accounts[account_id] = AccountRiskData(account_id)
            logger.info(f"Added account {account_id} to risk monitoring")
            
    async def start_monitoring(self):
        """Start the risk monitoring service"""
        if self.running:
            logger.warning("Risk monitoring already running")
            return
            
        self.running = True
        logger.info("Starting risk monitoring service")
        
        if self.demo_mode:
            # In demo mode, add some sample accounts
            self.add_account("DEMO123")
            self.add_account("DEMO456")
            self.add_account("DEMO789")
            
            # Start demo data generation
            asyncio.create_task(self._generate_demo_data())
        else:
            # In real mode, subscribe to Rithmic account updates
            if not self.rithmic_client:
                logger.error("No Rithmic client provided for risk monitoring")
                self.running = False
                return
                
            # Start real data collection
            asyncio.create_task(self._collect_real_data())
            
    async def stop_monitoring(self):
        """Stop the risk monitoring service"""
        self.running = False
        logger.info("Stopped risk monitoring service")
        
    async def _generate_demo_data(self):
        """Generate demo data for testing"""
        # Initial data
        accounts = list(self.accounts.keys())
        symbols = ["ES", "NQ", "CL", "GC", "ZB"]
        
        # Set initial positions
        for account_id in accounts:
            account = self.accounts[account_id]
            # Assign random positions to random symbols
            for symbol in random.sample(symbols, random.randint(1, 3)):
                position = random.randint(-10, 10)
                account.update_position(symbol, position)
                
            # Set initial P&L and margin
            initial_pnl = random.uniform(-3000, 3000)
            margin_used = random.uniform(5000, 20000)
            margin_available = random.uniform(10000, 50000)
            
            account.update_pnl(initial_pnl)
            account.update_margin(margin_used, margin_available)
        
        # Update loop
        while self.running:
            for account_id in accounts:
                account = self.accounts[account_id]
                
                # Update P&L with some random movement
                pnl_change = random.uniform(-500, 500)
                new_pnl = account.pnl + pnl_change
                account.update_pnl(new_pnl)
                
                # Occasionally update positions
                if random.random() < 0.2:  # 20% chance
                    symbol = random.choice(list(account.positions.keys()) if account.positions else symbols)
                    position_change = random.randint(-2, 2)
                    new_position = account.positions.get(symbol, 0) + position_change
                    account.update_position(symbol, new_position)
                
                # Update margin based on P&L and positions
                margin_used = account.margin_used + random.uniform(-500, 500)
                margin_used = max(5000, margin_used)  # Ensure minimum margin
                
                margin_available = account.margin_available + random.uniform(-200, 200)
                margin_available = max(0, margin_available)  # Can't go below 0
                
                account.update_margin(margin_used, margin_available)
            
            # Wait for next update
            await asyncio.sleep(self.update_interval)
            
    async def _collect_real_data(self):
        """Collect real data from Rithmic API"""
        # This would be implemented with actual Rithmic API calls
        # For now, we'll just log that we would be collecting real data
        logger.info("Would be collecting real data from Rithmic API")
        
        while self.running:
            try:
                # Here we would make API calls to get account data
                # For example:
                # account_data = await self.rithmic_client.get_account_data()
                # for account in account_data:
                #     self.update_account(account)
                
                # For now, just wait
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error collecting risk data: {e}")
                await asyncio.sleep(5)  # Wait longer on error
                
    def get_all_accounts_data(self) -> List[Dict[str, Any]]:
        """Get data for all accounts in a format suitable for display"""
        result = []
        
        for account_id, account in self.accounts.items():
            # Format positions as a string
            positions_str = ", ".join([f"{symbol}: {pos}" for symbol, pos in account.positions.items()])
            
            result.append({
                "account_id": account_id,
                "positions": positions_str,
                "total_position": account.get_total_position(),
                "pnl": account.pnl,
                "margin_used": account.margin_used,
                "margin_available": account.margin_available,
                "risk_level": account.risk_level,
                "risk_color": account.get_risk_color(),
                "last_update": account.last_update
            })
            
        return result


class RiskMonitoringUI:
    """UI components for risk monitoring"""
    
    def __init__(self, risk_monitor: RiskMonitor):
        self.risk_monitor = risk_monitor
        self.console = Console() if RICH_AVAILABLE else None
        self.live = None
        
    def create_risk_dashboard(self) -> Panel:
        """Create a rich dashboard for risk monitoring"""
        if not RICH_AVAILABLE:
            return None
            
        # Create main table for account overview
        accounts_table = Table(
            title="Account Risk Overview",
            show_header=True,
            header_style="bold magenta",
            box=True,
            expand=True
        )
        
        # Add columns
        accounts_table.add_column("Account", style="cyan", no_wrap=True)
        accounts_table.add_column("Positions", style="blue")
        accounts_table.add_column("P&L", style="green", justify="right")
        accounts_table.add_column("Margin Used", justify="right")
        accounts_table.add_column("Available", justify="right")
        accounts_table.add_column("Risk Level", no_wrap=True)
        accounts_table.add_column("Last Update", style="dim")
        
        # Get account data
        accounts_data = self.risk_monitor.get_all_accounts_data()
        
        # Sort by risk level (Critical, High, Medium, Low)
        risk_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        accounts_data.sort(key=lambda x: risk_order.get(x["risk_level"], 99))
        
        # Add rows
        for account in accounts_data:
            accounts_table.add_row(
                account["account_id"],
                account["positions"] if account["positions"] else "None",
                f"${account['pnl']:,.2f}",
                f"${account['margin_used']:,.2f}",
                f"${account['margin_available']:,.2f}",
                Text(account["risk_level"], style=account["risk_color"]),
                account["last_update"].strftime("%H:%M:%S")
            )
            
        # Create summary section
        total_pnl = sum(account["pnl"] for account in accounts_data)
        total_margin_used = sum(account["margin_used"] for account in accounts_data)
        total_margin_available = sum(account["margin_available"] for account in accounts_data)
        
        # Determine overall risk color
        if any(account["risk_level"] == "Critical" for account in accounts_data):
            overall_risk = "Critical"
            overall_color = "bold red"
        elif any(account["risk_level"] == "High" for account in accounts_data):
            overall_risk = "High"
            overall_color = "red"
        elif any(account["risk_level"] == "Medium" for account in accounts_data):
            overall_risk = "Medium"
            overall_color = "yellow"
        else:
            overall_risk = "Low"
            overall_color = "green"
            
        summary_text = f"""
[bold]Overall Risk Level:[/bold] [bold {overall_color}]{overall_risk}[/bold {overall_color}]
[bold]Total P&L:[/bold] ${total_pnl:,.2f}
[bold]Total Margin Used:[/bold] ${total_margin_used:,.2f}
[bold]Total Margin Available:[/bold] ${total_margin_available:,.2f}
[bold]Accounts Monitored:[/bold] {len(accounts_data)}
[bold]Last Update:[/bold] {datetime.now().strftime("%H:%M:%S")}
        """
        
        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(Panel(summary_text, title="Risk Summary", border_style="green"), size=8),
            Layout(Panel(accounts_table, title="Account Details", border_style="blue"))
        )
        
        return Panel(layout, title="🔍 Risk Live Monitoring Dashboard", border_style="cyan", padding=(1, 1))
        
    async def run_dashboard(self):
        """Run the live dashboard"""
        if not RICH_AVAILABLE:
            print("Rich library not available. Cannot display dashboard.")
            return
            
        try:
            with Live(self.create_risk_dashboard(), refresh_per_second=2, console=self.console) as live:
                self.live = live
                
                while self.risk_monitor.running:
                    # Update the dashboard
                    live.update(self.create_risk_dashboard())
                    await asyncio.sleep(0.5)
                    
        except KeyboardInterrupt:
            print("\nExiting risk monitoring dashboard...")
        finally:
            self.live = None


async def run_risk_monitoring(rithmic_client=None):
    """
    Main entry point for risk monitoring
    
    Args:
        rithmic_client: Optional RithmicClient instance
    """
    # Create risk monitor
    risk_monitor = RiskMonitor(rithmic_client)
    
    # Start monitoring
    await risk_monitor.start_monitoring()
    
    # Create and run UI
    ui = RiskMonitoringUI(risk_monitor)
    
    try:
        # Run the dashboard
        await ui.run_dashboard()
    finally:
        # Stop monitoring when done
        await risk_monitor.stop_monitoring()