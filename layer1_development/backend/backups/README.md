# Enhanced Rithmic Admin Tool

## Overview

This package provides a modular system for managing Rithmic API operations, including connection management, symbol search, historical data download, and database operations.

## Recent Improvements

1. **Relative Imports**: All imports have been updated to use relative imports for better maintainability and to avoid import errors.

2. **Module Documentation**: Added comprehensive docstrings to all modules to clarify their purpose and dependencies.

3. **Error Handling for Imports**: Implemented proper error handling for import errors with helpful error messages and fallback mechanisms.

4. **Dependency Injection**: Implemented dependency injection patterns to make the code more testable and reduce tight coupling between modules.

5. **Local Database Implementation**: Added a local implementation of database functions to avoid dependency on shared modules.

## Module Structure

- **admin_core_classes.py**: Core data structures and UI components
- **admin_database.py**: Database operations and TimescaleDB integration
- **admin_display_manager.py**: Rich TUI display management
- **admin_operations.py**: Main business logic coordinator
- **admin_rithmic_connection.py**: Rithmic API connection management
- **admin_rithmic_historical.py**: Historical data operations
- **admin_rithmic_operations.py**: Rithmic operations coordinator
- **admin_rithmic_symbols.py**: Symbol search and management
- **enhanced_admin_rithmic.py**: Main application entry point

## Usage

```python
# Import the main module
from layer1_development.enhanced_rithmic_admin import RithmicAdminTUI, main

# Run the application
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Dependencies

- Rich: For terminal UI components
- SQLAlchemy: For database operations
- AsyncPG: For asynchronous PostgreSQL connections
- Async-Rithmic: For Rithmic API operations

## Error Handling

The package now includes comprehensive error handling for imports and operations, with helpful error messages and fallback mechanisms.

## Testing

All modules can now be tested independently due to the dependency injection pattern and reduced coupling between modules.