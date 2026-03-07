import os
import re
import glob

def run():
    # Read the template chunk from the python file
    with open('backend/agents/interview_coach_agent.py', 'r', encoding='utf-8') as f:
        agent_code = f.read()
    
    # Extract the replacement chunk from interview_coach_agent.py
    # We want everything from <!-- ═══ AI INTERVIEW CHAT ═══ --> to </html>
    match = re.search(r'(<!-- ═══ AI INTERVIEW CHAT ═══ -->.*</html>)', agent_code, re.DOTALL)
    if not match:
        print("Template not found in interview_coach_agent.py")
        return
    template_str = match.group(1)

    html_files = glob.glob('frontend/interview/*.html')
    updated = 0
    for file in html_files:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract role and company
        title_match = re.search(r'<title>Mock Interview — (.*?) at (.*?)</title>', content)
        if not title_match:
            continue
        role = title_match.group(1)
        company = title_match.group(2)
        
        # We also need currentDifficulty, default to medium
        difficulty = "medium"

        # Replace in the template string
        new_chunk = template_str.replace('{company}', company).replace('{role}', role).replace('{difficulty}', difficulty)
        
        # Find the split point in the existing html
        split_idx = content.find('<!-- ═══ AI INTERVIEW CHAT ═══ -->')
        if split_idx == -1:
            print(f"Chat section not found in {file}")
            continue
            
        new_content = content[:split_idx] + new_chunk
        
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        updated += 1
    
    print(f"Updated {updated} HTML files successfully.")

if __name__ == '__main__':
    run()
