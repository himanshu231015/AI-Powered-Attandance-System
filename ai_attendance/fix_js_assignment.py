import os

path = r'c:\Users\himan\Documents\05-College\AI Powered Attandance System\AI Powered Attandance System\ai_attendance\templates\student_portal\dashboard.html'

try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # The exact pattern observed in view_file
    # Note: indentation might vary, so we'll use a regex or flexible replace
    # But string replace is safest if we match exactly what we saw
    
    # Pattern 1: Newline and spaces
    broken_1 = "const currentData = {{ current_attendance_count }\n            };"
    replace_1 = "const currentData = {{ current_attendance_count }};"
    
    # Pattern 2: Maybe Windows line endings?
    broken_2 = "const currentData = {{ current_attendance_count }\r\n            };"
    
    # Pattern 3: More generic regex just in case
    import re
    # Match: const currentData = {{ current_attendance_count } [newlines/spaces] };
    pattern = re.compile(r'const currentData = \{\{ current_attendance_count \}\s+\};')
    
    new_content = pattern.sub('const currentData = {{ current_attendance_count }};', content)
    
    if new_content != content:
        print("Found and fixed using Regex.")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Success.")
    else:
        print("Pattern not found by Regex. Trying exact string replace...")
        if broken_1 in content:
            content = content.replace(broken_1, replace_1)
            print("Fixed using exact match (LF).")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        elif broken_2 in content:
            content = content.replace(broken_2, replace_1)
            print("Fixed using exact match (CRLF).")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            print("Could not find the broken pattern.")
            # Debugging: print the area
            idx = content.find('const currentData')
            if idx != -1:
                print("Context found in file:")
                print(repr(content[idx:idx+100]))

except Exception as e:
    print(f"Error: {e}")
