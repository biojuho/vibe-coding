import asyncio
from scrapers.jobplanet import JobplanetScraper
from config import ConfigManager
import json

async def main():
    config_mgr = ConfigManager()
    scraper = JobplanetScraper(config_mgr)
    
    await scraper.open()
    page = await scraper._new_page()
    
    api_url = "https://www.jobplanet.co.kr/api/v5/community/posts/13309"
    print(f"Fetching {api_url}")
    response = await page.goto(api_url)
    
    if response.status == 200:
        data = await response.json()
        print("Success!")
        with open("jobplanet_post_debug_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        print(f"Failed with status: {response.status}")
        
    await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
