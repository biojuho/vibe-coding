import argparse
import os
import json
import sys
from pathlib import Path

def create_server(args):
    """Scaffolds a new MCP server."""
    name = args.name
    lang = args.lang
    path = Path(args.path) / name
    
    if path.exists():
        print(f"Error: Directory '{path}' already exists.")
        sys.exit(1)
    
    os.makedirs(path)
    print(f"Creating {lang} MCP server '{name}' at {path}...")

    if lang == 'python':
        _create_python_server(path, name)
    elif lang == 'ts':
        _create_ts_server(path, name)
    
    print(f"[OK] Server '{name}' created successfully!")
    print(f"👉 Next steps:\n   cd {path}\n   (Follow instructions in README.md)")

def _create_python_server(path, name):
    # Requirements
    with open(path / "requirements.txt", "w", encoding='utf-8') as f:
        f.write("mcp\n")
    
    # Server code
    with open(path / "server.py", "w", encoding='utf-8') as f:
        f.write(f"""from mcp.server.fastmcp import FastMCP

mcp = FastMCP("{name}")

@mcp.tool()
def hello_world() -> str:
    \"\"\"Returns a friendly greeting.\"\"\"
    return "Hello from {name}!"

if __name__ == "__main__":
    mcp.run()
""")
    
    # README
    with open(path / "README.md", "w", encoding='utf-8') as f:
        f.write(f"""# {name} MCP Server

## Setup
1. Create venv: `python -m venv venv`
2. Activate venv: `venv\\Scripts\\activate`
3. Install deps: `pip install -r requirements.txt`

## Usage
Run with inspector:
`npx @modelcontextprotocol/inspector python server.py`
""")

def _create_ts_server(path, name):
    # package.json
    pkg = {
        "name": name,
        "version": "1.0.0",
        "type": "module",
        "scripts": {
            "build": "tsc",
            "start": "node dist/index.js"
        },
        "dependencies": {
            "@modelcontextprotocol/sdk": "^0.6.0",
            "zod": "^3.22.4"
        },
        "devDependencies": {
            "typescript": "^5.3.3",
            "@types/node": "^20.11.0"
        }
    }
    with open(path / "package.json", "w", encoding='utf-8') as f:
        json.dump(pkg, f, indent=2)
    
    # tsconfig.json
    tsconfig = {
        "compilerOptions": {
            "target": "ES2022",
            "module": "Node16",
            "moduleResolution": "Node16",
            "outDir": "./dist",
            "rootDir": "./src",
            "strict": True,
            "esModuleInterop": True
        }
    }
    with open(path / "tsconfig.json", "w", encoding='utf-8') as f:
        json.dump(tsconfig, f, indent=2)
    
    # Source dir
    os.makedirs(path / "src")
    
    # Server code
    with open(path / "src" / "index.ts", "w", encoding='utf-8') as f:
        f.write("""import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "My Server",
  version: "1.0.0"
});

server.tool(
  "hello-world",
  "A test tool",
  { name: z.string() },
  async ({ name }) => ({
    content: [{ type: "text", text: `Hello, ${name}!` }]
  })
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});
""")
    
    # README
    with open(path / "README.md", "w", encoding='utf-8') as f:
        f.write("""# TS MCP Server
        
## Setup
1. `npm install`
2. `npm run build`

## Usage
`node dist/index.js`
""")

def main():
    parser = argparse.ArgumentParser(description="Vibe Coding MCP Manager")
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # New Server Command
    new_parser = subparsers.add_parser('new', help='Create a new MCP server')
    new_parser.add_argument('name', help='Name of the server')
    new_parser.add_argument('--lang', choices=['python', 'ts'], default='python', help='Language (python or ts)')
    new_parser.add_argument('--path', default='.', help='Parent directory')
    new_parser.set_defaults(func=create_server)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
