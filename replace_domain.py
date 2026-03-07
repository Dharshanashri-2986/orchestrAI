import os
import re

old_domain = "https://orchestrai.onrender.com"
new_domain = "https://orchestrai-u3wt.onrender.com"

# Only target specific directories to avoid accidents
target_dirs = [
    "backend/agents",
    "application_packages",
    "database",
    "frontend"
]
target_files = [
    "fast_email.py",
    "render.yaml",
    ".env"
]

def replace_in_file(file_path):
    if not os.path.isfile(file_path):
        return
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    if old_domain in content:
        print(f"Replacing in {file_path}")
        new_content = content.replace(old_domain, new_domain)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

for d in target_dirs:
    for root, _, files in os.walk(d):
        for f in files:
            replace_in_file(os.path.join(root, f))

for f in target_files:
    replace_in_file(f)
