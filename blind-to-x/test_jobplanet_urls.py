import asyncio
from config import ConfigManager
from scrapers.jobplanet import JobplanetScraper

async def main():
    config_mgr = ConfigManager()
    scraper = JobplanetScraper(config_mgr)
    await scraper.open()
    
    page = await scraper._new_page()
    
    async def handle_response(response):
        try:
            if 'application/json' in response.headers.get('content-type', '') and response.request.resource_type in ['fetch', 'xhr']:
                with open("jobplanet_api_logs.txt", "a", encoding="utf-8") as f:
                    f.write(f"JSON Response: {response.url}\n")
        except Exception:
            pass
            
    page.on("response", handle_response)
    
    urls_to_test = [
        'https://www.jobplanet.co.kr/api/v5/community/posts/popular?limit=10&is_shuffle=true',
        'https://www.jobplanet.co.kr/api/v5/community/posts?limit=20&order_by=recent'
    ]
    
    for url in urls_to_test:
        print(f"\nVisiting {url} ...")
        response = await page.goto(url)
        if response and response.status == 403:
            print('-> 403 Blocked!')
        elif response and response.status == 404:
            print('-> 404 Empty Page')
        else:
            print('-> IT WORKS! No empty page. Status:', response.status if response else 'Unknown')
            if response and response.status == 200:
                json_data = await response.json()
                print('Data keys:', json_data.keys() if isinstance(json_data, dict) else 'Not a dict')
                posts = json_data.get('data', {}).get('posts', [])
                if posts:
                    print('Found', len(posts), 'posts')
                    print('First post ID:', posts[0].get('id'))
                    print('First post title:', posts[0].get('title'))
            
    await scraper.close()

if __name__ == '__main__':
    asyncio.run(main())
