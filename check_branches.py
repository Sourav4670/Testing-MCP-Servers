"""Check repository branches and file status"""

import requests

owner, repo = "Sourav4670", "Testing-MCP-Servers"

# Get all branches
branches_url = f'https://api.github.com/repos/{owner}/{repo}/branches'
print(f"Fetching branches from: {branches_url}\n")

response = requests.get(branches_url, timeout=20)
branches = response.json()

print(f"Branches available ({len(branches)}):")
for branch in branches:
    print(f"  - {branch['name']}")

# Check files on each branch
print("\n" + "=" * 60)
for branch in branches:
    branch_name = branch['name']
    api_url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/{branch_name}?recursive=1'
    
    response = requests.get(api_url, timeout=20)
    if response.status_code == 200:
        tree_data = response.json().get('tree', [])
        py_files = [item['path'] for item in tree_data if item['type'] == 'blob' and item['path'].endswith('.py')]
        
        print(f"\n{branch_name} - Python files ({len(py_files)}):")
        for f in py_files:
            print(f"  - {f}")
    else:
        print(f"\n{branch_name} - Error: {response.status_code}")
