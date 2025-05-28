# Enhanced Rithmic Admin Tool - PowerShell Launcher
# ===================================================

Write-Host "🚀 Enhanced Rithmic Admin Tool Launcher" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Set error action preference
$ErrorActionPreference = "Stop"

try {
    # Get the script directory and navigate to project root
    $ScriptDir = $PSScriptRoot
    $ProjectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ScriptDir))
    $AdminDir = "$ProjectRoot\layer1_development\enhanced_rithmic_admin"
    
    Write-Host "📁 Project Directory: $AdminDir" -ForegroundColor Yellow
    
    # Check if directory exists
    if (-not (Test-Path $AdminDir)) {
        throw "Admin directory not found: $AdminDir"
    }
    
    # Navigate to admin directory
    Set-Location $AdminDir
    Write-Host "✅ Navigated to admin directory" -ForegroundColor Green
    
    # Check for virtual environment
    $VenvPath = "$ProjectRoot\venv"
    $VenvActivate = "$VenvPath\Scripts\Activate.ps1"
    
    Write-Host "🔧 Checking virtual environment at: $VenvPath" -ForegroundColor Yellow
    
    if (-not (Test-Path $VenvActivate)) {
        throw "Virtual environment not found at: $VenvPath"
    }
    
    # Activate virtual environment
    Write-Host "🔧 Activating Python virtual environment..." -ForegroundColor Yellow
    & $VenvActivate
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to activate virtual environment"
    }
    
    Write-Host "✅ Virtual environment activated" -ForegroundColor Green
    Write-Host ""
    
    # Check if main application exists
    $MainApp = "src\enhanced_admin_rithmic.py"
    if (-not (Test-Path $MainApp)) {
        throw "Main application not found: $MainApp"
    }
    
    # Display menu
    Write-Host "📋 Choose an option:" -ForegroundColor Cyan
    Write-Host "   1. Run Enhanced Admin Tool" -ForegroundColor White
    Write-Host "   2. Run System Tests" -ForegroundColor White  
    Write-Host "   3. Run Pylint Check" -ForegroundColor White
    Write-Host "   4. Show Project Structure" -ForegroundColor White
    Write-Host "   5. Exit" -ForegroundColor White
    Write-Host ""
    
    $choice = Read-Host "Enter your choice (1-5)"
    
    switch ($choice) {
        "1" {
            Write-Host "🎮 Starting Enhanced Rithmic Admin Tool..." -ForegroundColor Green
            Write-Host "💡 Use Test Connections to see the improved results display!" -ForegroundColor Yellow
            Write-Host ""
            python $MainApp
        }
        "2" {
            Write-Host "🧪 Running system tests..." -ForegroundColor Green
            Write-Host ""
            if (Test-Path "tests\final_verification.py") {
                python "tests\final_verification.py"
            } else {
                Write-Host "❌ Test file not found" -ForegroundColor Red
            }
        }
        "3" {
            Write-Host "🔍 Running pylint check..." -ForegroundColor Green
            Write-Host ""
            if (Test-Path "scripts\run_pylint_check.py") {
                python "scripts\run_pylint_check.py"
            } else {
                Write-Host "❌ Pylint script not found" -ForegroundColor Red
            }
        }
        "4" {
            Write-Host "📂 Project Structure:" -ForegroundColor Green
            Get-ChildItem -Directory | ForEach-Object { 
                Write-Host "  📁 $($_.Name)" -ForegroundColor Yellow
            }
        }
        "5" {
            Write-Host "👋 Goodbye!" -ForegroundColor Cyan
            exit 0
        }
        default {
            Write-Host "❌ Invalid choice. Please run the script again." -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Host ""
    Write-Host "✅ Operation completed!" -ForegroundColor Green
    
} catch {
    Write-Host ""
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "🔧 Troubleshooting:" -ForegroundColor Yellow
    Write-Host "   • Make sure you're running from the project directory" -ForegroundColor White
    Write-Host "   • Ensure virtual environment exists at: $ProjectRoot\venv" -ForegroundColor White
    Write-Host "   • Check that all files are in their correct locations" -ForegroundColor White
    Write-Host ""
    exit 1
} finally {
    # Return to original location
    if ($PSScriptRoot) {
        Set-Location $PSScriptRoot
    }
}

Read-Host "Press Enter to exit"