At the beginning of each conversation, please follow these rules:

1. Python Environment:
   - Always activate the virtual environment before executing Python commands
   - Use the command: `.\venv\Scripts\activate` (Windows) before any Python execution
   - Don't use && in Powershell scripts

2. Rithmic API Usage:
   - Reference the official async_rithmic documentation for all Rithmic-related functionality
   - Follow the patterns in "Connecting to Rithmic", "Market Data API", and "History Data API" documentation
     - https://async-rithmic.readthedocs.io/en/latest/historical_data.html
     - https://async-rithmic.readthedocs.io/en/latest/connection.html
     - https://async-rithmic.readthedocs.io/en/latest/realtime_data.html
   - Ensure proper connection and error handling for all Rithmic API calls
   - Avoid using deprecated functions or methods
   - Keep track of open connections and close them properly after used

3. Code Quality:
   - Include error handling in all code examples
   - Use async/await patterns correctly for asynchronous operations
   - Follow PEP 8 style guidelines for Python code
   - Add descriptive comments for complex operations
   - Write modular and reusable code where applicable
   - Test code thoroughly before sharing it with others
   - Be mindful of performance implications when writing code
   - Optimize code for readability and maintainability

4. Problem Solving:
   - Analyze the full context before suggesting solutions
   - Provide step-by-step explanations for complex fixes
   - When possible, offer multiple approaches to solving problems
   - Explain the reasoning behind your recommendations

5. Documentation:
   - Include links to relevant documentation when appropriate
   - Explain any non-obvious API behaviors or requirements
   - Document any workarounds for known limitations

6. Use the folder futures-trading-system\layer1_development\backend

7. (If needed) Create and use folder structure for new files. f.e. outputs --> output, logging --> logs, testscripts --> tests, etc...

8. When fixing a error, just replace the lines within the files that are causing errors. Do not change anything else.

9. execute pylint, mypy, black (if it doesn't exist in the venv install it) on the file you are working and put the output into a file called command_output-(datetime.now).txt. Then read the output files and fix the issues found by the commands.

10. when new files are created, then use the approbiate folders. f.e. fix_imports.py should be placed in the folder fix_imports.
    - If there is no folder yet create one.
    - If there is already a folder but the file name does not match the folder name, rename the file to match the folder name.
    - If there is already a folder and the file name matches the folder name, place the file in the correct folder.
    - If there is already a folder and the file name does not match the folder name, create a new folder with the same name as the file and move the file into the new folder.

Please confirm you understand these rules at the beginning of our conversation.