# Rithmic Enhanced Admin Tool - Setup Guide

## Problem Solved

You were experiencing a **"attempted relative import with no known parent package"** error. This happens when Python modules use relative imports (`from .module import ...`) but are run directly as scripts rather than as part of a package.

## What I Fixed

### 1. **Import Issues Fixed**
- ✅ Changed relative imports to absolute imports in all modules
- ✅ Added proper path configuration in the main script
- ✅ Created a new main script: `enhanced_admin_rithmic_fixed.py`

### 2. **Requirements Created**
- ✅ `requirements.txt` - Complete list of dependencies
- ✅ `requirements_core.txt` - Essential dependencies only
- ✅ All versions compatible with Python 3.11.9

### 3. **Troubleshooting Tools**
- ✅ `setup_check.py` - Diagnostic script to check your environment
- ✅ Detailed setup instructions

## Quick Start

### Step 1: Activate Virtual Environment
```bash
# In your project directory
.\venv\Scripts\activate
```

### Step 2: Install Dependencies
```bash
# Install core requirements
pip install -r requirements_core.txt

# OR install all requirements (includes dev tools)
pip install -r requirements.txt
```

### Step 3: Run Diagnostics
```bash
# Check if everything is set up correctly
python setup_check.py
```

### Step 4: Run the Fixed Application
```bash
# Use the fixed version
python enhanced_admin_rithmic_fixed.py
```

## Requirements Details

### Core Dependencies (requirements_core.txt)
```
rich==13.7.1                    # Terminal UI library
SQLAlchemy==2.0.30             # SQL toolkit and ORM
asyncpg==0.29.0                # PostgreSQL async driver
psycopg2-binary==2.9.9         # PostgreSQL adapter
pandas==2.2.2                  # Data manipulation
numpy==1.26.4                  # Numerical computing
keyboard==0.13.5               # Global hotkeys
pynput==1.7.6                  # Input control
pytz==2024.1                   # Timezone definitions
python-dotenv==1.0.1           # Environment variables
colorlog==6.8.2                # Colored logging
```

### Additional Dependencies (requirements.txt)
Includes everything above plus development tools, testing frameworks, and optional enhancements.

## Troubleshooting

### Common Issues and Solutions

#### 1. **Import Errors**
**Problem**: `ModuleNotFoundError` or import errors
**Solution**: 
```bash
python setup_check.py check
pip install -r requirements_core.txt
```

#### 2. **Relative Import Errors**
**Problem**: "attempted relative import with no known parent package"
**Solution**: Use the fixed script: `enhanced_admin_rithmic_fixed.py`

#### 3. **Missing async_rithmic**
**Problem**: Cannot import async_rithmic
**Solution**: 
```bash
# Install from your source (adjust URL as needed)
pip install async-rithmic

# OR if you have it locally
pip install -e /path/to/async-rithmic
```

#### 4. **Database Connection Issues**
**Problem**: Cannot connect to TimescaleDB
**Solution**: 
- Ensure PostgreSQL/TimescaleDB is running
- Check connection parameters in your config
- Run database initialization: Menu option 5

#### 5. **Keyboard Input Not Working**
**Problem**: Keyboard navigation doesn't work
**Solution**: 
```bash
# Try installing both keyboard libraries
pip install keyboard pynput

# Run with admin privileges if needed (Windows)
```

## File Structure

```
enhanced_rithmic_admin/
├── enhanced_admin_rithmic_fixed.py    # Fixed main script (USE THIS)
├── enhanced_admin_rithmic.py          # Original (has import issues)
├── admin_core_classes.py              # Core data structures
├── admin_database.py                  # Database operations
├── admin_display_manager.py           # UI display management
├── admin_operations.py                # Business logic
├── admin_rithmic_connection.py        # Rithmic connection mgmt
├── admin_rithmic_historical.py        # Historical data download
├── admin_rithmic_operations.py        # Rithmic operations coordinator
├── admin_rithmic_symbols.py           # Symbol search and management
├── requirements.txt                   # All dependencies
├── requirements_core.txt              # Essential dependencies only
├── setup_check.py                     # Diagnostic tool
└── README.md                          # This file
```

## Usage Instructions

### Menu Navigation
- **Arrow Keys** or **k/j**: Navigate up/down
- **Enter/Space**: Execute selected operation
- **1-5**: Direct menu selection
- **q/ESC/Ctrl+C**: Quit

### Menu Options
1. **Test Connections** - Verify database and Rithmic connections
2. **Search Symbols** - Find and validate trading symbols
3. **Download Historical Data** - Download market data to database
4. **View Database** - Browse stored data and statistics
5. **Initialize Database** - Set up TimescaleDB tables
6. **Exit** - Quit the application

## Environment Setup

### Required Environment Variables (Optional)
Create a `.env` file or set these in your environment:

```bash
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=trading_db
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=your_password

# Rithmic Configuration (or use config files)
RITHMIC_USERNAME=your_username
RITHMIC_PASSWORD=your_password
```

## Configuration Files

Ensure you have the Rithmic configuration file:
```
config/chicago_gateway_config.py
```

This should contain your Rithmic connection settings.

## Testing the Installation

Run the diagnostic script to verify everything is working:

```bash
# Run full diagnostic
python setup_check.py

# Install missing packages automatically
python setup_check.py install

# Just check status
python setup_check.py check
```

## Version Compatibility

- **Python**: 3.11.9 (recommended) or 3.11+
- **Operating System**: Windows, Linux, macOS
- **Database**: PostgreSQL with TimescaleDB extension

## Support

If you encounter issues:

1. Run `python setup_check.py` to diagnose problems
2. Check that all required files exist in the directory
3. Ensure your virtual environment is activated
4. Verify that async_rithmic is properly installed
5. Check your Rithmic configuration files

## Changes Made

### Files Modified
- ✅ Fixed relative imports in all modules
- ✅ Created `enhanced_admin_rithmic_fixed.py` with proper path handling
- ✅ Updated `admin_display_manager.py` imports
- ✅ Fixed `admin_rithmic_historical.py` imports
- ✅ Fixed `admin_rithmic_operations.py` imports

### Files Created
- ✅ `requirements.txt` - Complete dependency list
- ✅ `requirements_core.txt` - Essential dependencies
- ✅ `setup_check.py` - Diagnostic and setup tool
- ✅ `README.md` - This documentation

## Success Indicators

When everything is working correctly, you should see:
- ✅ No import errors when starting the application
- ✅ Rich terminal UI with menu navigation
- ✅ Successful database and Rithmic connection tests
- ✅ All diagnostic checks passing

Now you should be able to run your Rithmic admin tool without import errors!
