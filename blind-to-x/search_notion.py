import os
from dotenv import load_dotenv
from notion_client import AsyncClient
import asyncio

load_dotenv()
try:
    notion = AsyncClient(auth=os.environ["NOTION_API_KEY"])
except Exception as e:
    print(f"Error initializing client: {e}")
    exit(1)

async def main():
    print("Searching for databases accessible to the integration...")
    try:
        results = await notion.search()
        databases = results.get("results", [])
        if not databases:
            print("No databases found. The integration has no access to any database.")
            return

        for db in databases:
            obj_type = db.get("object", "unknown")
            if obj_type not in ["database", "data_source"]:
                continue
            title_objs = db.get("title", [])
            title = "".join([t.get("plain_text", "") for t in title_objs]).encode("ascii", "ignore").decode()
            print(f"Found {obj_type} '{title}' (ID: {db['id']})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
