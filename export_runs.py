import requests, os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('GITHUB_TOKEN')
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
url = 'https://api.github.com/repos/Swathy1209/orchestrai-agent/actions/runs?per_page=5'
resp = requests.get(url, headers=headers)
with open('actions_log.txt', 'w', encoding='utf-8') as f:
    if resp.status_code == 200:
        for run in resp.json().get('workflow_runs', []):
            f.write(f"Name: {run.get('name')}\n")
            f.write(f"Status: {run.get('status')} | Conclusion: {run.get('conclusion')}\n")
            f.write(f"Created: {run.get('created_at')} | Updated: {run.get('updated_at')}\n")
            f.write("---\n")
    else:
        f.write(f"Error {resp.status_code}: {resp.text}\n")
