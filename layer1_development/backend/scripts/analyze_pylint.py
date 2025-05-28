"""
Pylint Error Analysis Script
Run this to manually identify and fix common pylint issues
"""
import ast
import os
import sys
from pathlib import Path

def analyze_file(file_path):
    """Analyze a Python file for common issues"""
    print(f"=== Analyzing {file_path.name} ===")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for syntax errors first
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"  SYNTAX ERROR: Line {e.lineno}: {e.msg}")
        return []
    
    issues = []
    lines = content.split('\n')
    
    # Check for common issues
    for i, line in enumerate(lines, 1):
        # Long lines
        if len(line) > 120:
            issues.append((i, "line-too-long", f"Line too long ({len(line)}/120)"))
        
        # Missing docstrings for functions/classes
        if line.strip().startswith(('def ', 'class ')) and not line.strip().endswith(':'):
            if i < len(lines) and not lines[i].strip().startswith('"""'):
                issues.append((i, "missing-docstring", "Missing docstring"))
        
        # Unused imports (simple check)
        if line.strip().startswith('from ') or (line.strip().startswith('import ') and ' as ' not in line):
            import_name = line.split()[-1].split('.')[0]
            if import_name not in content[lines.index(line)*len(line):]:
                issues.append((i, "unused-import", f"Potentially unused import: {import_name}"))
        
        # Wildcard imports
        if 'import *' in line:
            issues.append((i, "wildcard-import", "Wildcard import should be avoided"))
        
        # Too many arguments (simple heuristic)
        if line.strip().startswith('def ') and line.count(',') > 6:
            issues.append((i, "too-many-arguments", "Function has many arguments"))
    
    # Print issues
    for line_no, code, msg in issues:
        print(f"  Line {line_no}: {code} - {msg}")
    
    if not issues:
        print("  No obvious issues found!")
    
    return issues

def main():
    """Main analysis function"""
    current_dir = Path('.')
    py_files = list(current_dir.glob('*.py'))
    py_files = [f for f in py_files if not f.name.startswith('run_') and not f.name.endswith('.backup')]
    
    print(f"Analyzing {len(py_files)} Python files...")
    print()
    
    all_issues = {}
    
    for py_file in py_files:
        issues = analyze_file(py_file)
        if issues:
            all_issues[py_file.name] = issues
        print()
    
    # Summary
    print("=== SUMMARY ===")
    if all_issues:
        for filename, issues in all_issues.items():
            print(f"{filename}: {len(issues)} issues")
        
        total_issues = sum(len(issues) for issues in all_issues.values())
        print(f"\nTotal issues found: {total_issues}")
    else:
        print("No issues found in any files!")

if __name__ == "__main__":
    main()
