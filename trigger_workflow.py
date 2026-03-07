import requests, os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('GITHUB_TOKEN')
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
username = os.getenv('GITHUB_USERNAME', 'Dharshanashri-2986')
repo = os.getenv('GITHUB_REPO', 'orchestrAI')
url = f'https://api.github.com/repos/{username}/{repo}/actions/workflows/career_agent.yml/dispatches'

resp = requests.post(url, headers=headers, json={"ref": "main"})
print(f"Trigger Status: {resp.status_code}")
print(resp.text)
