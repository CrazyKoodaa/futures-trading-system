"""
Display Manager for Rithmic Admin Tool
Handles all display and layout operations using Rich library components.
Integrates with modular Rithmic operations system.
"""

# Standard library imports
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

# Third-party imports
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.columns import Columns
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
from rich.markdown import Markdown
from rich.text import Text
from rich.table import Table
from rich.align import Align
from rich.live import Live
from rich.spinner import Spinner
from rich.tree import Tree
from rich.rule import Rule

# Local imports
from admin_core_classes import TUIComponents as CoreTUIComponents
from admin_core_classes import SystemStatus as CoreSystemStatus
from admin_core_classes import DownloadProgress as CoreDownloadProgress
from admin_core_classes import SymbolSearchResult as CoreSymbolSearchResult

# Local type aliases for type checking
TUIComponents = CoreTUIComponents
SystemStatus = CoreSystemStatus
DownloadProgress = CoreDownloadProgress
SymbolSearchResult = CoreSymbolSearchResult


class DisplayManager:
    """Manages all display and layout operations for the admin tool."""

    def __init__(
        self, console: Console, tui_components: TUIComponents, status: SystemStatus
    ):
        """Initialize the display manager.

        Args:
            console: Rich console instance for output
            tui_components: UI components container
            status: System status container
        """
        self.console = console
        self.tui_components = tui_components
        self.status = status
        self.layout: Optional[Layout] = None
        self.live = None
        self._setup_layout()

        # Import menu items from admin_core_classes
        from admin_core_classes import MENU_ITEMS

        self.menu_items = [item["title"] for item in MENU_ITEMS]

    def _setup_layout(self) -> None:
        """Set up the initial layout structure.

        Ensures self.layout is properly initialized with all required sections.
        """
        self.layout = Layout()

        # Create main sections with proper sizing
        self.layout.split(
            Layout(
                name="header", size=5
            ),  # Increased from 3 to 5 to show header properly
            Layout(name="body"),
            Layout(
                name="footer", size=30
            ),  # Increased from 10 to 18 for better status display
        )

        # Split the body into menu and content
        self.layout["body"].split_row(
            Layout(name="menu", ratio=1), Layout(name="content", ratio=4)
        )

        # Split the content into main and results
        self.layout["content"].split(
            Layout(name="main_content", ratio=2), Layout(name="results", ratio=2)
        )

    def render_layout(
        self, selected_menu_index: int = 0, results_content: str = ""
    ) -> Layout:
        """Render the complete layout with all panels.

        Args:
            selected_menu_index: Currently selected menu item index
            results_content: Content to display in results panel (unused in current implementation)

        Returns:
            Layout: The complete layout object
        """
        # Ensure layout is initialized
        if self.layout is None:
            self._setup_layout()

        # Final safety check - if layout is still None, create a new one
        if self.layout is None:
            self.layout = Layout()
            self._setup_layout()

        # At this point, self.layout is guaranteed to be a Layout object
        assert self.layout is not None, "Layout must be initialized"

        # Update all panels
        self.layout["header"].update(self.render_header())
        self.layout["menu"].update(self.render_menu(selected_menu_index))
        self.layout["main_content"].update(self.render_content())

        # Check if we have operation results to display
        if (
            hasattr(self.status, "last_operation_result")
            and self.status.last_operation_result
        ):
            # Check if the result looks like markdown (contains headers)
            result_text = str(self.status.last_operation_result)
            if "#" in result_text and "**" in result_text:
                # This looks like markdown, render it as such
                self.layout["results"].update(
                    Panel(
                        Markdown(result_text),
                        title="[bold green]Operation Results[/bold green]",
                        border_style="green",
                    )
                )
            else:
                # Regular text result
                self.layout["results"].update(
                    Panel(
                        Text(result_text),
                        title="[bold blue]Operation Results[/bold blue]",
                        border_style="blue",
                    )
                )
        elif results_content:
            self.layout["results"].update(
                Panel(Markdown(results_content), title="Results", border_style="green")
            )
        else:
            self.layout["results"].update(self.render_results())

        self.layout["footer"].update(self.render_status())

        # Return the complete layout - guaranteed to be Layout type
        return self.layout

    def render_header(self) -> Panel:
        """Render the header panel with system information.

        Returns:
            Panel: Rich panel with header content
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create header with multiple lines
        header_content = Text()
        header_content.append("🚀 Rithmic Admin Tool\n", style="bold cyan")
        header_content.append(f"🕒 {current_time}", style="white")

        # Add connection status indicators on the second line
        header_content.append(" | ")
        connection_status = (
            "● Connected" if self.status.rithmic_connected else "○ Disconnected"
        )
        status_color = "green" if self.status.rithmic_connected else "red"
        header_content.append(connection_status, style=status_color)

        # Add database status
        header_content.append(" | ")
        db_status = (
            "● DB Connected" if self.status.database_connected else "○ DB Disconnected"
        )
        db_color = "green" if self.status.database_connected else "red"
        header_content.append(db_status, style=db_color)

        # Add navigation help on third line
        header_content.append(
            "\n🎮 Navigation: ↑/↓ or j/k | Enter: Select | q: Quit", style="dim white"
        )

        return Panel(header_content, border_style="blue", padding=(0, 1))

    def render_menu(self, selected_index: int = 0) -> Panel:
        """Render the menu panel with navigation options.

        Args:
            selected_index: Currently selected menu item index

        Returns:
            Panel: Rich panel with menu content
        """
        # Use the menu_items we defined in __init__
        menu_text = Text()
        for idx, item in enumerate(self.menu_items):
            if idx > 0:
                menu_text.append("\n")

            if idx == selected_index:
                menu_text.append(f"▶ {item}", style="bold green")
            else:
                menu_text.append(f"  {item}")

        return Panel(menu_text, title="Menu", border_style="blue")

    def render_content(self) -> Panel:
        """Render the main content panel based on current selection.

        Returns:
            Panel: Rich panel with main content
        """
        # This would typically contain the main content for the selected menu item
        # For now, we'll just show a placeholder
        content_text = Text(
            "Main content area\n\nSelect an option from the menu to view content."
        )
        return Panel(content_text, title="Content", border_style="blue")

    def render_results(self) -> Panel:
        """Render the results panel with operation results.

        Returns:
            Panel: Rich panel with results content
        """
        # This would typically show results of operations
        results_text = Text("Results will appear here after operations complete.")
        return Panel(results_text, title="Results", border_style="green")

    def render_status(self) -> Panel:
        """Render the status panel with system status information.

        Returns:
            Panel: Rich panel with status content
        """
        status_text = Text()

        # Active operations
        if self.status.active_operations:
            status_text.append("Active operations:\n", style="bold")
            for op_id, op_status in self.status.active_operations.items():
                status_text.append(f"  {op_id}: {op_status}\n")
        else:
            status_text.append("No active operations\n")

        # Last operation result with enhanced formatting
        if self.status.last_operation_result:
            result = self.status.last_operation_result
            # Check if it's an error message
            if "[ERROR]" in result:
                status_text.append("❌ ", style="red bold")
                status_text.append(result.replace("[ERROR] ", ""), style="red")
            elif "[WARNING]" in result:
                status_text.append("⚠️  ", style="yellow bold")
                status_text.append(result.replace("[WARNING] ", ""), style="yellow")
            elif "[INFO]" in result:
                status_text.append("ℹ️  ", style="cyan bold")
                status_text.append(result.replace("[INFO] ", ""), style="cyan")
            else:
                status_text.append(f"Last result: {result}")
            status_text.append("\n")

        # Session duration - use the correct property name
        if hasattr(self.status, "session_duration_time"):
            session_duration = self.status.session_duration_time
            if callable(session_duration):
                session_duration = session_duration()
            status_text.append(f"Session duration: {session_duration}\n")

        # Connection details
        if self.status.connection_details:
            status_text.append("\nConnection details:\n")
            for key, value in self.status.connection_details.items():
                status_text.append(f"  {key}: {value}\n")

        # Determine panel style based on last message
        border_style = "blue"
        title_style = "Status"
        if self.status.last_operation_result:
            if "[ERROR]" in self.status.last_operation_result:
                border_style = "red"
                title_style = "[red]Status - Error[/red]"
            elif "[WARNING]" in self.status.last_operation_result:
                border_style = "yellow"
                title_style = "[yellow]Status - Warning[/yellow]"

        return Panel(status_text, title=title_style, border_style=border_style)

    def update_progress_display(self, symbol: str, progress: DownloadProgress) -> None:
        """Update progress display for a specific symbol.

        Args:
            symbol: Symbol being processed
            progress: Progress information
        """
        # Update the progress in system status
        self.status.download_progress[symbol] = progress

        # Update the TUI components with the progress info
        self.tui_components.update_progress_info(symbol, progress)

        # If we have a live display, update it
        if hasattr(self, "live_display") and self.live_display:
            # Ensure we have a valid layout before updating
            if self.layout is not None:
                self.live_display.update(self.layout)

    def show_results(self, content: str, title: str = "Results") -> None:
        """Show results in the results panel.

        Args:
            content: Content to display
            title: Title for the results panel
        """
        self.results_content = content
        self.results_title = title

        # Switch to 4-panel layout if not already
        if hasattr(self, "current_layout") and self.current_layout == "3-panel":
            self.current_layout = "4-panel"
            self._setup_layout()

    def clear_results(self) -> None:
        """Clear the results panel and switch back to 3-panel layout."""
        if hasattr(self, "results_content"):
            self.results_content = ""
        if hasattr(self, "results_title"):
            self.results_title = "Results"

        if hasattr(self, "current_layout") and self.current_layout == "4-panel":
            self.current_layout = "3-panel"
            self._setup_layout()

    def create_progress_table(self, download_progress: Dict[str, Any]) -> Table:
        """Create a progress table for download operations.

        Args:
            download_progress: Dictionary of symbol progress data

        Returns:
            Rich table with progress information
        """
        table = Table(
            title="Download Progress", show_header=True, header_style="bold magenta"
        )
        table.add_column("Symbol", style="cyan", width=8)
        table.add_column("Step", style="yellow", width=20)
        table.add_column("Progress", style="green", width=20)
        table.add_column("Status", style="white", width=15)

        # Avoid cell variable issue in loop
        for symbol, progress in download_progress.items():
            if hasattr(progress, "current_step"):
                step = progress.current_step
                progress_percent = getattr(progress, "progress_percent", 0)
                # Ensure progress_percent is a number before multiplication
                if isinstance(progress_percent, (int, float)):
                    percent = f"{progress_percent * 100:.1f}%"
                else:
                    percent = "0.0%"
                is_complete_val = getattr(progress, "download_complete", False)
                status = "✅ Complete" if is_complete_val else "🔄 In Progress"
            else:
                # Handle simple progress values
                step = "Downloading"
                percent = (
                    f"{progress * 100:.1f}%" if isinstance(progress, float) else "0%"
                )
                status = "🔄 In Progress"

            table.add_row(symbol, step, percent, status)

        return table

    def create_symbol_table(
        self, symbols_data: List[Union[Dict[str, Any], Any]]
    ) -> Table:
        """Create a table for symbol information.

        Args:
            symbols_data: List of symbol data dictionaries or SymbolSearchResult objects

        Returns:
            Rich table with symbol information
        """
        table = Table(
            title="Available Symbols", show_header=True, header_style="bold cyan"
        )
        table.add_column("Symbol", style="cyan", width=10)
        table.add_column("Exchange", style="yellow", width=10)
        table.add_column("Name", style="white", width=30)
        table.add_column("Expiration", style="green", width=12)
        table.add_column("Product", style="magenta", width=10)

        # Avoid cell variable issue by creating local variable
        for symbol_data in symbols_data:
            # Handle both dict and object types
            if hasattr(symbol_data, "symbol"):
                # SymbolSearchResult object
                table.add_row(
                    getattr(symbol_data, "symbol", "N/A"),
                    getattr(symbol_data, "exchange", "N/A"),
                    getattr(symbol_data, "name", "N/A"),
                    str(getattr(symbol_data, "expiration", "N/A")),
                    getattr(symbol_data, "product_code", "N/A"),
                )
            else:
                # Dictionary
                table.add_row(
                    symbol_data.get("symbol", "N/A"),
                    symbol_data.get("exchange", "N/A"),
                    symbol_data.get("name", "N/A"),
                    str(symbol_data.get("expiration", "N/A")),
                    symbol_data.get("product_code", "N/A"),
                )

        return table

    def create_connection_status_panel(self) -> Panel:
        """Create a detailed connection status panel.

        Returns:
            Rich panel with connection status details
        """
        content = Text()

        # Rithmic connection (Connection Module)
        if self.status.rithmic_connected:
            content.append("🟢 Rithmic Connection", style="bold green")
            content.append(" [Connection Module]\n", style="dim cyan")
            content.append("  Status: Connected\n", style="green")
            content.append("  Gateway: Chicago\n", style="white")

            # Show connection details if available
            if self.status.connection_details:
                for key, value in self.status.connection_details.items():
                    content.append(f"  {key}: {value}\n", style="white")
        else:
            content.append("🔴 Rithmic Connection", style="bold red")
            content.append(" [Connection Module]\n", style="dim cyan")
            content.append("  Status: Disconnected\n", style="red")
            content.append("  Gateway: Not Connected\n", style="dim red")

        content.append("\n")

        # Database connection (Operations Module)
        if self.status.database_connected:
            content.append("🟢 Database Connection", style="bold green")
            content.append(" [Operations Module]\n", style="dim cyan")
            content.append("  Status: Connected\n", style="green")
            content.append("  Type: TimescaleDB\n", style="white")
        else:
            content.append("🔴 Database Connection", style="bold red")
            content.append(" [Operations Module]\n", style="dim cyan")
            content.append("  Status: Disconnected\n", style="red")
            content.append("  Type: TimescaleDB (Unavailable)\n", style="dim red")

        content.append("\n")

        # Module Status Overview
        content.append("📋 Module Status Overview:\n", style="bold white")

        modules = [
            (
                "Connection",
                "admin_rithmic_connection.py",
                self.status.rithmic_connected,
            ),
            (
                "Symbols",
                "admin_rithmic_symbols.py",
                bool(self.status.symbol_search_results),
            ),
            (
                "Historical",
                "admin_rithmic_historical.py",
                bool(self.status.download_progress),
            ),
            (
                "Operations",
                "admin_rithmic_operations.py",
                self.status.database_connected,
            ),
        ]

        for module_name, module_file, is_active in modules:
            icon = "🟢" if is_active else "🔴"
            status_text = "Active" if is_active else "Inactive"
            status_color = "green" if is_active else "red"

            content.append(f"  {icon} {module_name}: ", style="white")
            content.append(f"{status_text}\n", style=status_color)
            content.append(f"    File: {module_file}\n", style="dim white")

        return Panel(
            content,
            title="[bold white]Connection & Module Details[/bold white]",
            border_style="blue",
            padding=(1, 2),
        )

    def show_loading_spinner(self, message: str = "Loading...") -> None:
        """Show a loading spinner with message.

        Args:
            message: Loading message to display
        """
        spinner = Spinner("dots", text=message, style="cyan")
        self.console.print(spinner)

    def render_error_message(self, error: str, title: str = "Error") -> Panel:
        """Render an error message panel.

        Args:
            error: Error message to display
            title: Title for the error panel

        Returns:
            Rich panel with error message
        """
        error_text = Text()
        error_text.append("❌ ", style="bold red")
        error_text.append(error, style="red")

        return Panel(
            error_text,
            title=f"[bold red]{title}[/bold red]",
            border_style="red",
            padding=(1, 2),
        )

    def render_success_message(self, message: str, title: str = "Success") -> Panel:
        """Render a success message panel.

        Args:
            message: Success message to display
            title: Title for the success panel

        Returns:
            Rich panel with success message
        """
        success_text = Text()
        success_text.append("✅ ", style="bold green")
        success_text.append(message, style="green")

        return Panel(
            success_text,
            title=f"[bold green]{title}[/bold green]",
            border_style="green",
            padding=(1, 2),
        )

    def start_live_display(self) -> None:
        """Start live display mode for real-time updates."""
        if not hasattr(self, "live_display") or not self.live_display:
            # Ensure layout is ready before starting live display
            if self.layout is None:
                self._setup_layout()

            # Create and start the live display
            self.live_display = Live(
                self.render_layout(),
                console=self.console,
                refresh_per_second=2,  # Reduced refresh rate for stability
                auto_refresh=True,
            )
            self.live_display.start()

    def stop_live_display(self) -> None:
        """Stop live display mode."""
        if hasattr(self, "live_display") and self.live_display:
            self.live_display.stop()
            self.live_display = None

    def update_live_display(self, selected_menu_index: int = 0) -> None:
        """Update the live display with current state.

        Args:
            selected_menu_index: Currently selected menu item
        """
        if hasattr(self, "live_display") and self.live_display:
            # Update the live display with a fresh layout render
            try:
                updated_layout = self.render_layout(selected_menu_index)
                # updated_layout is guaranteed to be Layout type from render_layout
                self.live_display.update(updated_layout)
            except Exception:
                # If live update fails, fall back to basic update
                pass

    def create_module_status_tree(self) -> Tree:
        """Create a tree view of module status and operations.

        Returns:
            Rich tree with module hierarchy and status
        """
        tree = Tree("🏗️ Rithmic Admin System")

        # Connection Module
        connection_branch = tree.add(
            "🔗 Connection Module (admin_rithmic_connection.py)"
        )
        if self.status.rithmic_connected:
            connection_branch.add("✅ Rithmic Gateway: Connected")
            connection_branch.add("🌐 Chicago Gateway Active")
        else:
            connection_branch.add("❌ Rithmic Gateway: Disconnected")
            connection_branch.add("🔴 No Active Connection")

        # Symbols Module
        symbols_branch = tree.add("🔍 Symbols Module (admin_rithmic_symbols.py)")
        if self.status.symbol_search_results:
            symbols_branch.add(
                f"✅ Symbol Search: {len(self.status.symbol_search_results)} results"
            )
        else:
            symbols_branch.add("❌ Symbol Search: No results")

        # Historical Module
        historical_branch = tree.add(
            "📊 Historical Module (admin_rithmic_historical.py)"
        )
        if self.status.download_progress:
            historical_branch.add(
                f"✅ Downloads: {len(self.status.download_progress)} active"
            )
            # Avoid cell variable issue
            for symbol, progress in self.status.download_progress.items():
                if hasattr(progress, "current_step"):
                    completion_pct = getattr(progress, "completion_percentage", 0)
                    # Ensure completion_pct is a number before multiplication
                    if callable(completion_pct):
                        try:
                            pct_val = completion_pct()
                            percentage_val = (
                                pct_val * 100
                                if isinstance(pct_val, (int, float))
                                else 0
                            )
                        except:
                            percentage_val = 0
                    elif isinstance(completion_pct, (int, float)):
                        percentage_val = completion_pct * 100
                    else:
                        percentage_val = 0
                    historical_branch.add(
                        f"📈 {symbol}: {progress.current_step} ({percentage_val:.1f}%)"
                    )
        else:
            historical_branch.add("❌ Downloads: None active")

        # Operations Module
        operations_branch = tree.add(
            "🗃️ Operations Module (admin_rithmic_operations.py)"
        )
        if self.status.database_connected:
            operations_branch.add("✅ Database: Connected")
            operations_branch.add("📁 TimescaleDB Active")
        else:
            operations_branch.add("❌ Database: Disconnected")
            operations_branch.add("🔴 No Database Connection")

        return tree

    def create_historical_progress_panel(self) -> Panel:
        """Create a panel showing historical data download progress.

        Returns:
            Rich panel with progress information
        """
        content = Text()

        if not self.status.download_progress:
            content.append("No active downloads", style="dim")
            return Panel(content, title="Historical Data Progress", border_style="blue")

        content.append("Active Downloads:\n\n", style="bold")

        for symbol, progress in self.status.download_progress.items():
            # Symbol header
            content.append(f"{symbol}: ", style="cyan bold")

            if progress.download_complete:
                content.append("Complete ✅\n", style="green")
            elif hasattr(progress, "error") and progress.error:
                content.append(f"Error ❌ - {progress.error}\n", style="red")
            else:
                content.append("In Progress 🔄\n", style="yellow")

            # Progress details
            if hasattr(progress, "current_step"):
                content.append(f"  Step: {progress.current_step}\n", style="white")

            # Use the completion_percentage property - check if it's callable
            if hasattr(progress, "completion_percentage"):
                if callable(progress.completion_percentage):
                    pct = progress.completion_percentage() * 100
                    progress_val = progress.completion_percentage() / 100
                else:
                    pct = progress.completion_percentage
                    progress_val = progress.completion_percentage / 100
            else:
                pct = 0
                progress_val = 0
            content.append(f"  Progress: {pct:.1f}%\n", style="white")

            # Simple progress bar
            bar_width = 20
            # Ensure progress_val is a number before multiplication
            if isinstance(progress_val, (int, float)):
                filled = int(bar_width * progress_val)
            else:
                filled = 0
            content.append("  [")
            content.append("=" * filled, style="green")
            content.append(" " * (bar_width - filled))
            content.append("]\n\n")

            # Show elapsed time if available
            if hasattr(progress, "elapsed_time"):
                if callable(progress.elapsed_time):
                    elapsed = progress.elapsed_time()
                    if elapsed is not None:
                        content.append(f"  Time elapsed: {elapsed}\n", style="white")
                else:
                    elapsed = progress.elapsed_time
                    if elapsed is not None:
                        content.append(f"  Time elapsed: {elapsed}\n", style="white")

        return Panel(content, title="Historical Data Progress", border_style="blue")

    def set_operation_result(
        self, result: Union[Dict[str, Any], str, List, None, Any]
    ) -> None:
        """Set the result of an operation for display.

        Args:
            result: Operation result data, can be a dictionary, string, list, None, or any other type
        """
        # Handle different types of input
        if isinstance(result, dict):
            # Dictionary case - extract message if available
            message = result.get("message", "Operation completed")
            status = result.get("status", "info")
            if status.lower() in ["error", "warning", "info"]:
                message = f"[{status.upper()}] {message}"
        elif isinstance(result, str):
            # String case
            message = result if result else "Operation completed"
        elif isinstance(result, list):
            # List case - convert to string representation
            message = f"List result: {', '.join(str(item) for item in result)}"
        elif result is None:
            # None case
            message = "No result returned"
        else:
            # Any other type - convert to string
            message = f"{type(result).__name__}: {str(result)}"

        self.status.last_operation_result = message

        # If we have a live display, update it
        if hasattr(self, "live_display") and self.live_display:
            try:
                updated_layout = self.render_layout()
                self.live_display.update(updated_layout)
            except Exception:
                pass  # Ignore update errors

    def show_welcome_message(self) -> None:
        """Display welcome message within the TUI layout instead of printing."""
        # Set a welcome message in the status instead of printing
        self.status.last_operation_result = "Welcome to Rithmic Admin Tool! Use ↑/↓ or j/k to navigate, Enter to select."

        # Update the display to show the welcome message
        if hasattr(self, "live_display") and self.live_display:
            self.update_live_display(0)
