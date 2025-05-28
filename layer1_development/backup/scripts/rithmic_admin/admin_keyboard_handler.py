"""
Keyboard Input Handler for Enhanced Rithmic Admin Tool
Manages all keyboard interactions and navigation
"""

import asyncio
import logging
import queue
from typing import Callable, Optional, Dict, Any

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

logger = logging.getLogger("rithmic_admin.keyboard")

class KeyboardHandler:
    """Handles keyboard input and navigation for the admin tool"""
    
    def __init__(self, menu_items_count: int):
        self.menu_items_count = menu_items_count
        self.current_menu_item = 0
        self.running = True
        
        # Callbacks
        self.on_menu_change: Optional[Callable[[int], None]] = None
        self.on_menu_execute: Optional[Callable[[int], None]] = None
        self.on_shutdown: Optional[Callable[[], None]] = None
        
        # Key state tracking
        self.key_pressed = {}
        self.setup_complete = False
        
        # Event queue for main event loop processing
        self.event_queue = queue.Queue()
        
        if KEYBOARD_AVAILABLE:
            self.setup_keyboard_handlers()
    
    def setup_keyboard_handlers(self):
        """Setup all keyboard event handlers"""
        try:
            # Clear any existing handlers
            keyboard.unhook_all()
            
            # Navigation keys
            keyboard.on_press_key('up', self._handle_up_arrow)
            keyboard.on_press_key('down', self._handle_down_arrow)
            keyboard.on_press_key('enter', self._handle_enter_key)
            keyboard.on_press_key('esc', self._handle_escape_key)
            
            # Number key shortcuts (1-5 for menu items, 0 for exit)
            for i in range(1, 6):
                keyboard.on_press_key(str(i), lambda e, num=i: self._handle_number_key(num-1))
            keyboard.on_press_key('0', lambda e: self._handle_number_key(self.menu_items_count-1))
            
            # Control keys
            keyboard.on_press_key('ctrl+c', self._handle_ctrl_c)
            keyboard.on_press_key('q', self._handle_quit_key)
            
            # Help key
            keyboard.on_press_key('h', self._handle_help_key)
            keyboard.on_press_key('?', self._handle_help_key)
            
            # Clear/refresh keys
            keyboard.on_press_key('c', self._handle_clear_key)
            keyboard.on_press_key('r', self._handle_refresh_key)
            
            self.setup_complete = True
            logger.info("Keyboard handlers setup successfully")
            
        except Exception as e:
            logger.warning(f"Keyboard setup failed: {e}")
            self.setup_complete = False
    
    def _handle_up_arrow(self, event):
        """Handle up arrow key press"""
        try:
            if not self.running:
                return
                
            self.current_menu_item = (self.current_menu_item - 1) % self.menu_items_count
            if self.on_menu_change:
                self.on_menu_change(self.current_menu_item)
                
        except Exception as e:
            logger.error(f"Error handling up arrow: {e}")
    
    def _handle_down_arrow(self, event):
        """Handle down arrow key press"""
        try:
            if not self.running:
                return
                
            self.current_menu_item = (self.current_menu_item + 1) % self.menu_items_count
            if self.on_menu_change:
                self.on_menu_change(self.current_menu_item)
                
        except Exception as e:
            logger.error(f"Error handling down arrow: {e}")
    
    def _handle_enter_key(self, event):
        """Handle enter key press"""
        try:
            if not self.running:
                return
                
            if self.on_menu_execute:
                # Add to event queue for processing by main event loop
                self.event_queue.put({
                    'type': 'execute',
                    'menu_item': self.current_menu_item
                })
                logger.info(f"Menu item {self.current_menu_item} execution queued")
                
        except Exception as e:
            logger.error(f"Error handling enter key: {e}")
    
    def _handle_escape_key(self, event):
        """Handle escape key press"""
        try:
            if self.on_shutdown:
                # Add to event queue for processing by main event loop
                self.event_queue.put({
                    'type': 'shutdown'
                })
                logger.info("Shutdown request queued")
        except Exception as e:
            logger.error(f"Error handling escape key: {e}")
    
    def _handle_number_key(self, menu_index: int):
        """Handle number key press for direct menu selection"""
        try:
            if not self.running:
                return
                
            if 0 <= menu_index < self.menu_items_count:
                self.current_menu_item = menu_index
                if self.on_menu_change:
                    self.on_menu_change(self.current_menu_item)
                
                # Add to event queue for processing by main event loop
                self.event_queue.put({
                    'type': 'execute',
                    'menu_item': menu_index,
                    'delay': 0.1  # Short delay before execution
                })
                logger.info(f"Menu item {menu_index} selection queued")
                
        except Exception as e:
            logger.error(f"Error handling number key {menu_index}: {e}")
    
    def _handle_ctrl_c(self, event):
        """Handle Ctrl+C for graceful shutdown"""
        try:
            if self.on_shutdown:
                # Add to event queue for processing by main event loop
                self.event_queue.put({
                    'type': 'shutdown',
                    'source': 'ctrl+c'
                })
                logger.info("Ctrl+C shutdown request queued")
        except Exception as e:
            logger.error(f"Error handling Ctrl+C: {e}")
    
    def _handle_quit_key(self, event):
        """Handle 'q' key for quit"""
        try:
            if self.on_shutdown:
                # Add to event queue for processing by main event loop
                self.event_queue.put({
                    'type': 'shutdown',
                    'source': 'quit_key'
                })
                logger.info("Quit request queued")
        except Exception as e:
            logger.error(f"Error handling quit key: {e}")
    
    def _handle_help_key(self, event):
        """Handle help key press"""
        try:
            help_text = """
## 🎯 Keyboard Shortcuts Help

### Navigation
- **↑/↓ Arrow Keys**: Navigate menu items
- **Enter**: Execute selected menu item
- **1-5**: Direct menu selection
- **0**: Exit application

### Control
- **Esc**: Exit application
- **Ctrl+C**: Force exit
- **q**: Quit application
- **h** or **?**: Show this help
- **c**: Clear results
- **r**: Refresh display

### Menu Items
1. Test Connections (DB + Rithmic)
2. Search Symbols & Check Contracts
3. Download Historical Data
4. View TimescaleDB Data
5. Initialize/Setup Database
0. Exit
            """
            # This would trigger a help display - implement based on your needs
            logger.info("Help requested - keyboard shortcuts displayed")
            
        except Exception as e:
            logger.error(f"Error handling help key: {e}")
    
    def _handle_clear_key(self, event):
        """Handle clear key to clear results"""
        try:
            # This would trigger results clearing - implement based on your needs
            logger.info("Clear requested")
        except Exception as e:
            logger.error(f"Error handling clear key: {e}")
    
    def _handle_refresh_key(self, event):
        """Handle refresh key to refresh display"""
        try:
            # This would trigger display refresh - implement based on your needs
            logger.info("Refresh requested")
        except Exception as e:
            logger.error(f"Error handling refresh key: {e}")
    
    async def _delayed_execute(self, menu_index: int, delay: float):
        """Execute menu item after a delay"""
        try:
            await asyncio.sleep(delay)
            if self.running and self.on_menu_execute:
                if asyncio.iscoroutinefunction(self.on_menu_execute):
                    await self.on_menu_execute(menu_index)
                else:
                    self.on_menu_execute(menu_index)
        except Exception as e:
            logger.error(f"Error in delayed execute: {e}")
    
    async def _execute_menu_item(self, menu_index: int):
        """Execute menu item asynchronously"""
        try:
            if self.on_menu_execute:
                if asyncio.iscoroutinefunction(self.on_menu_execute):
                    await self.on_menu_execute(menu_index)
                else:
                    self.on_menu_execute(menu_index)
        except Exception as e:
            logger.error(f"Error executing menu item {menu_index}: {e}")
    
    async def _shutdown(self):
        """Handle shutdown request"""
        try:
            self.running = False
            if self.on_shutdown:
                # Check if on_shutdown is a coroutine function
                if asyncio.iscoroutinefunction(self.on_shutdown):
                    await self.on_shutdown()
                else:
                    self.on_shutdown()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def set_menu_change_callback(self, callback: Callable[[int], None]):
        """Set callback for menu item changes"""
        self.on_menu_change = callback
    
    def set_menu_execute_callback(self, callback: Callable[[int], None]):
        """Set callback for menu item execution"""
        self.on_menu_execute = callback
    
    def set_shutdown_callback(self, callback: Callable[[], None]):
        """Set callback for shutdown requests"""
        self.on_shutdown = callback
    
    def get_current_menu_item(self) -> int:
        """Get current selected menu item"""
        return self.current_menu_item
    
    def set_current_menu_item(self, index: int):
        """Set current menu item programmatically"""
        if 0 <= index < self.menu_items_count:
            self.current_menu_item = index
            if self.on_menu_change:
                self.on_menu_change(self.current_menu_item)
    
    def is_available(self) -> bool:
        """Check if keyboard handling is available"""
        return KEYBOARD_AVAILABLE and self.setup_complete
    
    def cleanup(self):
        """Clean up keyboard handlers"""
        try:
            if KEYBOARD_AVAILABLE:
                keyboard.unhook_all()
            self.running = False
            logger.info("Keyboard handlers cleaned up")
        except Exception as e:
            logger.warning(f"Error during keyboard cleanup: {e}")
    
    def get_status_info(self) -> dict:
        """Get keyboard handler status information"""
        return {
            'available': self.is_available(),
            'current_menu_item': self.current_menu_item,
            'menu_items_count': self.menu_items_count,
            'running': self.running,
            'setup_complete': self.setup_complete,
            'queued_events': self.event_queue.qsize()
        }
        
    async def process_event_queue(self):
        """Process all events in the queue
        
        This method should be called regularly from the main event loop
        to process keyboard events.
        """
        try:
            # Process all events in the queue
            while not self.event_queue.empty():
                event = self.event_queue.get_nowait()
                
                if event['type'] == 'execute':
                    menu_item = event.get('menu_item', self.current_menu_item)
                    delay = event.get('delay', 0)
                    
                    # Apply delay if needed
                    if delay > 0:
                        await asyncio.sleep(delay)
                    
                    # Execute the menu item
                    if self.on_menu_execute and self.running:
                        await self._execute_menu_item(menu_item)
                
                elif event['type'] == 'shutdown':
                    # Execute shutdown
                    if self.on_shutdown:
                        await self._shutdown()
                
                # Mark the event as processed
                self.event_queue.task_done()
                
        except Exception as e:
            logger.error(f"Error processing event queue: {e}")

class SimpleInputHandler:
    """Fallback input handler for systems without keyboard library"""
    
    def __init__(self, menu_items_count: int):
        self.menu_items_count = menu_items_count
        self.current_menu_item = 0
        self.running = True
    
    async def get_input(self) -> Optional[int]:
        """Get menu selection from user input"""
        try:
            choice = input(f"\nEnter choice (1-{self.menu_items_count-1}, 0=Exit): ").strip()
            
            if choice.isdigit():
                choice_num = int(choice)
                
                # Map 0 to exit (last menu item)
                if choice_num == 0:
                    return self.menu_items_count - 1
                
                # Map 1-N to menu items
                if 1 <= choice_num <= self.menu_items_count - 1:
                    return choice_num - 1
            
            return None
            
        except (EOFError, KeyboardInterrupt):
            return self.menu_items_count - 1  # Return exit option
        except Exception as e:
            logger.error(f"Error getting input: {e}")
            return None
    
    def is_available(self) -> bool:
        """Simple input is always available"""
        return True
    
    def cleanup(self):
        """No cleanup needed for simple input"""
        pass
    
    def get_status_info(self) -> dict:
        """Get simple input handler status"""
        return {
            'available': True,
            'current_menu_item': self.current_menu_item,
            'menu_items_count': self.menu_items_count,
            'running': self.running,
            'type': 'simple'
        }