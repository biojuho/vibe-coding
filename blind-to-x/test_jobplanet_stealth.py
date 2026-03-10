import asyncio
import logging
logging.basicConfig(level=logging.INFO)
from config import ConfigManager
from scrapers.jobplanet import JobplanetScraper

async def main():
    config_mgr = ConfigManager()
    
    # We set headless to True by default, but you could change it if debug is needed
    scraper = JobplanetScraper(config_mgr)
    
    try:
        print("--- Testing Feed Fetch ---")
        await scraper.open()
        
        # trending URLs
        urls = await scraper.get_trending_urls(limit=2)
        print("Trending URLs found:", urls)
        
        if not urls:
            print("No URLs found, fallback failed or blocked entirely!")
            return
            
        print("\n--- Testing Single Post Scrape ---")
        post = await scraper.scrape_post(urls[0])
        print("\nPost Scrape Result:")
        for k, v in post.items():
            if k == "content":
                print(f"  {k}: {v[:100]}...")  # truncate
            else:
                print(f"  {k}: {v}")
                
    except Exception as e:
        print(f"Test failed with error: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
