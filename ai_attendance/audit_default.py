import re

path = r'c:\Users\himan\Documents\05-College\AI Powered Attandance System\AI Powered Attandance System\ai_attendance\templates\student_portal\dashboard.html'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("--- AUDIT START ---")
for i, line in enumerate(lines):
    if 'default' in line:
        print(f"LINE {i+1}: {line.strip()}")
print("--- AUDIT END ---")
