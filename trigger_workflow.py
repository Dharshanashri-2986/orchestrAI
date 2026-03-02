import requests, os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('GITHUB_TOKEN')
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
url = 'https://api.github.com/repos/Swathy1209/orchestrai-agent/actions/workflows/career_agent.yml/dispatches'

resp = requests.post(url, headers=headers, json={"ref": "main"})
print(f"Trigger Status: {resp.status_code}")
print(resp.text)
