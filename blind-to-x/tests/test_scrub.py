import asyncio
import re
from playwright.async_api import async_playwright

async def main():
    with open("raw2.html", "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # Scrub ALL scripts!
    html_content = re.sub(r'<script.*?</script>', '', html_content, flags=re.DOTALL)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        
        url = "https://www.teamblind.com/kr/post/%ED%98%95%EB%93%A4-%EB%82%98-%EC%9D%B8%ED%85%8C%EB%A6%AC%EC%96%B4-%EA%B3%B5%EC%82%AC-%EC%A4%91%EC%9D%B8%EB%8D%B0-guyg5nxl"
        async def intercept(route):
            await route.fulfill(body=html_content, content_type="text/html")
            
        await page.route(url, intercept)
        # Block external scripts too just in case
        await page.route("**/*.js", lambda r: r.abort())
        
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(2)  # Wait for CSS
        
        container = await page.query_selector('.contents')
        if container:
            print("SUCCESS! .contents PRESERVED!")
            await container.screenshot(path="scrubbed_screenshot.png")
            print("Screenshot saved!")
        else:
            print("STILL FAILED... The scrubbing didn't work.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
