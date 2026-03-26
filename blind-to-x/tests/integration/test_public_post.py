import asyncio
from blind_scraper import BlindScraper

import yaml

async def main():
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    scraper = BlindScraper(config)
    # "인테리어 공사 중인데" - Known public post
    url = "https://www.teamblind.com/kr/post/%ED%98%95%EB%93%A4-%EB%82%98-%EC%9D%B8%ED%85%8C%EB%A6%AC%EC%96%B4-%EA%B3%B5%EC%82%AC-%EC%A4%91%EC%9D%B8%EB%8D%B0-guyg5nxl"

    print(f"Scraping {url}...")
    result = await scraper.scrape_post(url)

    if result:
        print("Scrape SUCCESS!")
        print("Title:", result["title"])
        print("Screenshot Path:", result["screenshot_path"])
    else:
        print("Scrape FAILED.")

if __name__ == "__main__":
    asyncio.run(main())
