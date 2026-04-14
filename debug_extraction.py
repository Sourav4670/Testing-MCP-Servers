"""Debug script to simulate the full extraction process"""

import re
import requests
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

def http_get_text(url: str) -> str:
    """Fetch text with timeout; return empty string on failure."""
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            return response.text
        return ""
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def extract_python_tools(content: str, file_path: str) -> Dict[str, Any]:
    """Extract MCP tools from Python file"""
    file_tools = {}
    
    # ToolHandler style: super().__init__("tool_name")
    toolhandler_name_pattern = re.compile(
        r'super\(\)\.__init__\(\s*["\']([A-Za-z_][A-Za-z0-9_]*)["\']\s*\)'
    )
    
    for tool_name in toolhandler_name_pattern.findall(content):
        file_tools[tool_name] = {
            'file': file_path,
            'parameters': [],
            'return_type': 'unknown',
            'description': None,
            'docstring': None,
        }
        
        # Try to extract description from get_tool_description method
        get_tool_desc_match = re.search(
            r'def\s+get_tool_description\s*\([^)]*\)\s*(?:->\s*[^:]+)?\s*:\s*([\s\S]*?)(?=\n\s{0,4}def\s|\nclass\s|\Z)',
            content,
            re.MULTILINE
        )
        
        if get_tool_desc_match:
            method_body = get_tool_desc_match.group(1)
            
            # Extract description
            desc_match = re.search(
                r'description\s*=\s*\(?\s*["\']([^"\']*)["\']',
                method_body,
                re.DOTALL
            )
            if desc_match:
                desc_text = desc_match.group(1).strip()
                desc_text = re.sub(r'\s+', ' ', desc_text)
                file_tools[tool_name]['description'] = desc_text[:200]
            
            # Extract parameters from inputSchema properties
            if '"properties"' in method_body or "'properties'" in method_body:
                property_lines = re.findall(
                    r'["\']([A-Za-z_][A-Za-z0-9_]*)["\'](?:\s*:\s*)\{',
                    method_body
                )
                
                excluded = {'properties', 'type', 'string', 'number', 'integer', 'boolean', 'object', 'array', 'required'}
                params = [p for p in property_lines if p not in excluded]
                file_tools[tool_name]['parameters'] = params
    
    return file_tools

# Test with your repository
repo_url = "https://github.com/Sourav4670/Testing-MCP-Servers"
owner, repo = "Sourav4670", "Testing-MCP-Servers"
branch = "internet-speed-test"

print(f"Repository: {owner}/{repo} (branch: {branch})")
print("=" * 60)

# Get repository structure from GitHub API
api_url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1'
print(f"\nFetching structure from: {api_url}")

response = requests.get(api_url, timeout=20)
if response.status_code != 200:
    print(f"Error: {response.status_code}")
    exit(1)

tree_data = response.json().get('tree', [])
python_files = [item['path'] for item in tree_data if item['type'] == 'blob' and item['path'].endswith('.py') and 'test' not in item['path'].lower()]
doc_files = [item['path'] for item in tree_data if item['type'] == 'blob' and item['path'].lower() in ['readme.md', 'readme.rst', 'readme.txt']]

print(f"\nPython files found ({len(python_files)}):")
for f in python_files:
    print(f"  - {f}")

print(f"\nDocumentation files found ({len(doc_files)}):")
for f in doc_files:
    print(f"  - {f}")

# Process Python files concurrently
print(f"\nProcessing Python files...")
tools_dict = {}

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {}
    
    for file_path in python_files:
        file_url = f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}'
        future = executor.submit(lambda fp=file_path, fu=file_url: (fp, http_get_text(fu)))
        futures[future] = file_path
    
    for future in as_completed(futures):
        file_path, content = future.result()
        if content:
            file_tools = extract_python_tools(content, file_path)
            print(f"  {file_path}: Found {len(file_tools)} tools")
            for tool_name, tool_info in file_tools.items():
                if tool_name not in tools_dict:
                    tools_dict[tool_name] = tool_info

print(f"\n" + "=" * 60)
print(f"TOTAL TOOLS FOUND: {len(tools_dict)}")
print("\nTools Details:")
for tool_name, tool_info in tools_dict.items():
    print(f"\n✓ {tool_name}")
    print(f"  File: {tool_info.get('file')}")
    print(f"  Description: {tool_info.get('description')}")
    print(f"  Parameters: {tool_info.get('parameters')}")


