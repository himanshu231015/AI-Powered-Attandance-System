import re
import os

path = r'c:\Users\himan\Documents\05-College\AI Powered Attandance System\AI Powered Attandance System\ai_attendance\templates\student_portal\dashboard.html'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("--- DIAGNOSIS START ---")
issues_found = False
new_lines = []

# Regex to find '|default' potentially followed by spaces and a colon
# We want to normalize to '|default:'
# Also check for '|default' NOT followed by colon

regex_fix_spaces = re.compile(r'\|\s*default\s*:\s*')
regex_missing_arg = re.compile(r'\|\s*default\s*(?!:)')

for i, line in enumerate(lines):
    original_line = line
    
    if 'default' in line:
        # Check for missing colon
        if regex_missing_arg.search(line) and 'default:' not in line:
            print(f"LINE {i+1} POSSIBLE MISSING ARG: {line.strip()}")
            issues_found = True
        
        # Check for spaces
        if re.search(r'\|\s*default\s*:\s+', line):
             print(f"LINE {i+1} HAS SPACES: {line.strip()}")
             issues_found = True

        # Apply Fix: Remove spaces around default and colon
        # Replace '| default : ' with '|default:'
        line = regex_fix_spaces.sub('|default:', line)
        
        if line != original_line:
            print(f"FIXING LINE {i+1}:")
            print(f"  OLD: {original_line.strip()}")
            print(f"  NEW: {line.strip()}")

    new_lines.append(line)

print("--- DIAGNOSIS END ---")

if issues_found or lines != new_lines:
    print("Applying changes...")
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print("File updated successfully.")
    except Exception as e:
        print(f"Failed to write file: {e}")
else:
    print("No issues found or changes needed.")
