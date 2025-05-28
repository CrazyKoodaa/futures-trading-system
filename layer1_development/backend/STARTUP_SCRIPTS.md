# Enhanced Rithmic Admin - Startup Scripts

This directory contains startup scripts to easily launch the Enhanced Rithmic Admin Tool across different platforms.

## Available Scripts

### 🪟 Windows

#### PowerShell Script (Recommended)
```powershell
.\start_admin.ps1
```
- **Features**: Full error handling, colored output, menu system
- **Requirements**: PowerShell 5.1+ (Windows 10/11 default)
- **Path**: `enhanced_rithmic_admin/start_admin.ps1`

#### Batch Script (Legacy)
```cmd
scripts\run_enhanced_admin.bat
```
- **Features**: Simple menu system, basic error handling
- **Requirements**: Command Prompt/PowerShell
- **Path**: `enhanced_rithmic_admin/scripts/run_enhanced_admin.bat`

### 🐧 Linux/macOS

#### Shell Script
```bash
./start_admin.sh
```
- **Features**: Full error handling, colored output, menu system
- **Requirements**: Bash shell
- **Path**: `enhanced_rithmic_admin/start_admin.sh`

## First Time Setup

### Linux/macOS Only
Make the shell script executable:
```bash
chmod +x start_admin.sh
```

### Windows PowerShell Execution Policy
If you get an execution policy error, run this **once** as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## What These Scripts Do

1. **🔧 Environment Setup**
   - Automatically navigate to the correct project directory
   - Activate the Python virtual environment (`../../venv`)
   - Verify all required files and paths exist

2. **📋 Interactive Menu**
   - Run Enhanced Admin Tool (main application)
   - Run System Tests (verification scripts)
   - Run Pylint Check (code quality analysis)
   - Show Project Structure
   - Exit gracefully

3. **⚠️ Error Handling**
   - Clear error messages with troubleshooting hints
   - Verify virtual environment exists
   - Check for missing files before execution
   - Graceful fallback and cleanup

## Usage Examples

### Quick Start (Windows)
```powershell
# Navigate to project directory
cd C:\Users\nobody\myProjects\git\futures-trading-system\layer1_development\enhanced_rithmic_admin

# Run PowerShell script
.\start_admin.ps1
```

### Quick Start (Linux)
```bash
# Navigate to project directory
cd /path/to/futures-trading-system/layer1_development/enhanced_rithmic_admin

# Make executable (first time only)
chmod +x start_admin.sh

# Run script
./start_admin.sh
```

## File Structure Requirements

These scripts expect the following structure:
```
futures-trading-system/
├── venv/                           # Virtual environment
└── layer1_development/
    └── enhanced_rithmic_admin/
        ├── src/                    # Source code
        │   └── enhanced_admin_rithmic.py
        ├── tests/                  # Test scripts
        ├── scripts/                # Utility scripts
        ├── start_admin.ps1         # Windows PowerShell script
        └── start_admin.sh          # Linux/macOS shell script
```

## Troubleshooting

### Virtual Environment Not Found
- **Problem**: Scripts can't find `../../venv`
- **Solution**: Ensure virtual environment exists at project root
- **Create venv**: `python -m venv venv` (from project root)

### Permission Denied (Linux/macOS)
- **Problem**: `./start_admin.sh: Permission denied`
- **Solution**: `chmod +x start_admin.sh`

### PowerShell Execution Policy (Windows)
- **Problem**: `start_admin.ps1 cannot be loaded`
- **Solution**: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Module Import Errors
- **Problem**: Python can't find modules after reorganization
- **Solution**: Scripts automatically handle paths; if issues persist, check that files are in correct `/src/` folder

## Advanced Usage

### Running Directly Without Menu
```bash
# Windows PowerShell
& .\start_admin.ps1 -Choice 1

# Linux (modify script to accept parameters)
./start_admin.sh --direct
```

### Custom Virtual Environment Path
Edit the scripts to modify the `VENV_PATH` variable if your virtual environment is located elsewhere.

---

**Created**: 2025-05-28  
**Compatible**: Windows 10/11, Linux, macOS  
**Dependencies**: Python 3.8+, Virtual Environment
