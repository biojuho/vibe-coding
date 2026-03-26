import asyncio
from playwright.async_api import async_playwright

async def main():
    url = "https://www.teamblind.com/kr/post/%ED%98%95%EB%93%A4-%EB%82%98-%EC%9D%B8%ED%85%8C%EB%A6%AC%EC%96%B4-%EA%B3%B5%EC%82%AC-%EC%A4%91%EC%9D%B8%EB%8D%B0-guyg5nxl"
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        # Using desktop user agent
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        print("Navigating...")
        await page.goto(url, wait_until="domcontentloaded")
        print("Waiting a bit...")
        await asyncio.sleep(5)

        # Save HTML
        content = await page.content()
        with open("test_page.html", "w", encoding="utf-8") as f:
            f.write(content)

        # Save Screenshot
        await page.screenshot(path="test_screenshot.png", full_page=True)
        print("Saved test_page.html and test_screenshot.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
