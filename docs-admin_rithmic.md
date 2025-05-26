# Test connections
python admin_rithmic.py -t

# Search for symbols
python admin_rithmic.py -S "NG?5"

# Check contract existence for a specific symbol
python admin_rithmic.py -s "NGM5" -c

# Download historical data for a specific symbol
python admin_rithmic.py -s "NGM5" -d

# Stream live data for a specific symbol
python admin_rithmic.py -s "NGM5" -l

# Combine multiple operations
python admin_rithmic.py -t -s "NGM5" -c -d
