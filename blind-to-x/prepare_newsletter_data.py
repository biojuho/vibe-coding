import asyncio
import yaml
import traceback
from pipeline.notion_upload import NotionUploader

async def main():
    try:
        with open("config.yaml", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        print("Initializing NotionUploader...")
        uploader = NotionUploader(config)
        await uploader.ensure_schema()

        print(f"Collection Kind: {uploader.collection_kind}")
        print(f"Database ID: {uploader.database_id}")

        print("Searching for recent pages (using native search client)...")
        response = await uploader.client.search(
            query="",
            filter={"value": "page", "property": "object"},
            sort={"direction": "descending", "timestamp": "last_edited_time"},
            page_size=20
        )

        # Filter for pages belonging to our database
        all_results = response.get("results", [])
        print(f"Total pages from search: {len(all_results)}")
        results = []
        for r in all_results:
            parent = r.get("parent", {})
            p_type = parent.get("type")
            p_id = parent.get(p_type, "") if p_type else ""
            print(f"Parent type: {p_type}, ID: {p_id}")
            if p_type in ["database_id", "data_source_id"] and p_id.replace("-", "") == uploader.database_id.replace("-", ""):
                results.append(r)

        results = results[:5]  # limit to 5
        print(f"Found {len(results)} items in the target database")
        for r in results:
            pid = r["id"]
            props = r.get("properties", {})
            title_prop = props.get(uploader.props.get("title", ""), {})
            title = ""
            if "title" in title_prop and title_prop["title"]:
                title = title_prop["title"][0]["plain_text"]

            print(f"Updating [{title}] ({pid})")
            # Ensure it has a newsletter body and approved status
            updates = {
                "status": "발행승인",
                "review_status": "발행승인",
                "newsletter_body": f"뉴스레터 테스트 초안입니다. 제목: {title}\n\n이것은 자동 발행 테스트를 위한 더미 텍스트입니다.",
                "final_rank_score": 95,
                "publishability_score": 90
            }
            await uploader.update_page_properties(pid, updates)
            print("  -> Done")
    except Exception as e:
        print(f"Failed with exception: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
