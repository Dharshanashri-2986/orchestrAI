import os
import yaml
from pprint import pprint

def read_yaml(f):
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    return {}

base_url = "https://orchestrai.onrender.com"
cover_letter_data = read_yaml("database/cover_letter_index.yaml")
optimization_data = read_yaml("database/resume_optimizations.yaml")

cl_list = cover_letter_data.get("cover_letters", [])
cl_lookup = {
    (item.get("company", ""), item.get("role", "")): (
        item.get('link') if item.get('link', '').startswith('http') else
        (f"{base_url}{item.get('link')}" if item.get('link', '').startswith('/') else f"{base_url}/{item.get('link')}")
    ) if item.get('link') else "#"
    for item in cl_list[:5]
}

opt_list = optimization_data if isinstance(optimization_data, list) else []
opt_lookup = {
    (item.get("company", ""), item.get("role", "")): (
        item.get('optimized_resume_link') if item.get('optimized_resume_link', '').startswith('http') else
        (f"{base_url}{item.get('optimized_resume_link')}" if item.get('optimized_resume_link', '').startswith('/') else f"{base_url}/{item.get('optimized_resume_link')}")
    ) if item.get('optimized_resume_link') else "#"
    for item in opt_list[:5]
}

print("--- Cover Letter Links ---")
pprint(cl_lookup)
print("\n--- Optimized Resume Links ---")
pprint(opt_lookup)
