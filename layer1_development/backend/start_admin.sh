#!/bin/bash

# Enhanced Rithmic Admin Tool - Shell Launcher
# =============================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

echo -e "${CYAN}🚀 Enhanced Rithmic Admin Tool Launcher${NC}"
echo -e "${CYAN}=========================================${NC}"
echo ""

# Set error handling
set -e

# Function to handle errors
handle_error() {
    echo ""
    echo -e "${RED}❌ Error: $1${NC}"
    echo ""
    echo -e "${YELLOW}🔧 Troubleshooting:${NC}"
    echo -e "${WHITE}   • Make sure you're running from the project directory${NC}"
    echo -e "${WHITE}   • Ensure virtual environment exists at: \$PROJECT_ROOT/venv${NC}"
    echo -e "${WHITE}   • Check that all files are in their correct locations${NC}"
    echo -e "${WHITE}   • Make sure the script has execute permissions: chmod +x start_admin.sh${NC}"
    echo ""
    exit 1
}

# Get script directory and project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
ADMIN_DIR="$PROJECT_ROOT/layer1_development/enhanced_rithmic_admin"

echo -e "${YELLOW}📁 Project Directory: $ADMIN_DIR${NC}"

# Check if directory exists
if [ ! -d "$ADMIN_DIR" ]; then
    handle_error "Admin directory not found: $ADMIN_DIR"
fi

# Navigate to admin directory
cd "$ADMIN_DIR" || handle_error "Failed to navigate to admin directory"
echo -e "${GREEN}✅ Navigated to admin directory${NC}"

# Check for virtual environment
VENV_PATH="$PROJECT_ROOT/venv"
VENV_ACTIVATE="$VENV_PATH/bin/activate"

echo -e "${YELLOW}🔧 Checking virtual environment at: $VENV_PATH${NC}"

if [ ! -f "$VENV_ACTIVATE" ]; then
    handle_error "Virtual environment not found at: $VENV_PATH"
fi

# Activate virtual environment
echo -e "${YELLOW}🔧 Activating Python virtual environment...${NC}"
source "$VENV_ACTIVATE" || handle_error "Failed to activate virtual environment"

echo -e "${GREEN}✅ Virtual environment activated${NC}"
echo ""

# Check if main application exists
MAIN_APP="src/enhanced_admin_rithmic.py"
if [ ! -f "$MAIN_APP" ]; then
    handle_error "Main application not found: $MAIN_APP"
fi

# Display menu
echo -e "${CYAN}📋 Choose an option:${NC}"
echo -e "${WHITE}   1. Run Enhanced Admin Tool${NC}"
echo -e "${WHITE}   2. Run System Tests${NC}"
echo -e "${WHITE}   3. Run Pylint Check${NC}"
echo -e "${WHITE}   4. Show Project Structure${NC}"
echo -e "${WHITE}   5. Exit${NC}"
echo ""

read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        echo -e "${GREEN}🎮 Starting Enhanced Rithmic Admin Tool...${NC}"
        echo -e "${YELLOW}💡 Use Test Connections to see the improved results display!${NC}"
        echo ""
        python "$MAIN_APP"
        ;;
    2)
        echo -e "${GREEN}🧪 Running system tests...${NC}"
        echo ""
        if [ -f "tests/final_verification.py" ]; then
            python "tests/final_verification.py"
        else
            echo -e "${RED}❌ Test file not found${NC}"
        fi
        ;;
    3)
        echo -e "${GREEN}🔍 Running pylint check...${NC}"
        echo ""
        if [ -f "scripts/run_pylint_check.py" ]; then
            python "scripts/run_pylint_check.py"
        else
            echo -e "${RED}❌ Pylint script not found${NC}"
        fi
        ;;
    4)
        echo -e "${GREEN}📂 Project Structure:${NC}"
        for dir in */; do
            if [ -d "$dir" ]; then
                echo -e "${YELLOW}  📁 ${dir%/}${NC}"
            fi
        done
        ;;
    5)
        echo -e "${CYAN}👋 Goodbye!${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ Invalid choice. Please run the script again.${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Operation completed!${NC}"

# Ask user to press Enter before exiting
echo ""
read -p "Press Enter to exit..."
