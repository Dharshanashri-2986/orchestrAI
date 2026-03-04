import re

fp = r'backend\agents\execution_agent.py'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()

# Use regex to replace from the STEP 6 comment through the closing triple-quote
new_block = '''    # STEP 6: Generate full HTML email
    html = f"""
    <html>
    <head><style>
      body {{ font-family: Arial, sans-serif; font-size: 13px; background: #f8f9fa; margin: 0; padding: 20px; }}
      h2, h3 {{ color: #1a237e; }}
      table {{ border-collapse: collapse; width: 100%; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
      th {{ background: #1a237e; color: white; padding: 10px 8px; text-align: left; font-size: 12px; white-space: nowrap; }}
      tr:nth-child(even) td {{ background: #f5f5f5; }}
    </style></head>
    <body>
        <h2>&#x1F916; Daily AI &amp; Data Science Internship Report</h2>
        <table>
            <tr>
                <th>Company</th>
                <th>Role</th>
                <th>Location</th>
                <th>Required Skills</th>
                <th>Apply</th>
                <th>Match Score</th>
                <th>Skill Gap</th>
                <th>Learning Roadmap</th>
                <th>Generated Assets</th>
                <th>&#x1F512; Security Risk</th>
                <th>&#x1F310; Main Portfolio</th>
                <th>&#x1F3AF; Custom Portfolio</th>
            </tr>
            {rows}
        </table>

        <h3>&#x1F9ED; Career Strategy Recommendation</h3>
        <p><b>Goal:</b> {strategy_goal}</p>
        <p><b>This Week\'s Focus:</b></p>
        <ul>{strategy_html}</ul>

        <h3>&#x1F510; Security Insights &mdash; All GitHub Repos</h3>
        <ul>{sec_insights_html}</ul>
    </body>
    </html>
    """'''

# Replace from '# STEP 6' to the closing triple-quote of the html block
pattern = r'    # STEP 6: Generate full HTML email\s+html = f""".*?"""'
new_content = re.sub(pattern, new_block, content, flags=re.DOTALL)

if new_content == content:
    print("ERROR: Pattern not found!")
else:
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: File updated!")
