
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Force UTF-8 output for Windows console
sys.stdout.reconfigure(encoding='utf-8')

# Add site-packages from parent directory's venv if needed
# We assume this script is run from the project root
# We need to access the notebooklm-mcp venv we set up earlier
NOTEBOOKLM_VENV_LIB = r"c:\Users\박주호\Desktop\Vibe coding\infrastructure\notebooklm-mcp\venv\Lib\site-packages"
if os.path.exists(NOTEBOOKLM_VENV_LIB):
    sys.path.append(NOTEBOOKLM_VENV_LIB)

try:
    from notebooklm_mcp.api_client import NotebookLMClient
    from notebooklm_mcp.auth import AuthTokens
    import httpx
except ImportError as e:
    print(f"Error importing modules: {e}")
    # Fallback for dev environment without venv linked
    print("Please run this script with the correct python environment")
    sys.exit(1)

# Configuration
OUTPUT_FILE = Path("public/dashboard_data.json")
NOTEBOOKLM_TOKEN_PATH = r"c:\Users\박주호\Desktop\Vibe coding\infrastructure\notebooklm-mcp\tokens\auth.json"
GITHUB_TOKEN = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "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") # Fallback for dev

def fetch_github_repos():
    print("Fetching GitHub repositories...")
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = "https://api.github.com/user/repos?sort=updated&per_page=10"
    
    try:
        response = httpx.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        repos = response.json()
        
        # Simplify data for dashboard
        simplified = []
        for repo in repos:
            simplified.append({
                "id": repo["id"],
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo["description"],
                "html_url": repo["html_url"],
                "language": repo["language"],
                "stargazers_count": repo["stargazers_count"],
                "updated_at": repo["updated_at"]
            })
        print(f"  - Found {len(simplified)} repositories")
        return simplified
    except Exception as e:
        print(f"  - Error fetching GitHub repos: {e}")
        return []

def fetch_notebooklm_notebooks():
    print("Fetching NotebookLM notebooks...")
    if not os.path.exists(NOTEBOOKLM_TOKEN_PATH):
        print(f"  - Token file not found at {NOTEBOOKLM_TOKEN_PATH}")
        return []
        
    try:
        with open(NOTEBOOKLM_TOKEN_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        tokens = AuthTokens.from_dict(data)
        client = NotebookLMClient(
            cookies=tokens.cookies,
            csrf_token=tokens.csrf_token,
            session_id=tokens.session_id
        )
        
        notebooks = client.list_notebooks()
        
        simplified = []
        for nb in notebooks:
            simplified.append({
                "id": nb.id,
                "title": nb.title,
                "source_count": nb.source_count,
                "url": nb.url,
                "ownership": nb.ownership,
                "sources": [{
                    "id": s.get("id"),
                    "title": s.get("title"),
                    "type": s.get("type")
                } for s in nb.sources] if nb.sources else []
            })
            
        print(f"  - Found {len(simplified)} notebooks")
        return simplified
    except Exception as e:
        print(f"  - Error fetching NotebookLM notebooks: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    print(f"Starting data sync at {datetime.now().isoformat()}...")
    
    # Create public dir if not exists
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    
    data = {
        "last_updated": datetime.now().isoformat(),
        "github": fetch_github_repos(),
        "notebooklm": fetch_notebooklm_notebooks()
    }
    
    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
