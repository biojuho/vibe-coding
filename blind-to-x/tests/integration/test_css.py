import asyncio
from playwright.async_api import async_playwright
from curl_cffi.requests import AsyncSession

async def main():
    url = "https://www.teamblind.com/kr/post/%EB%82%B4-%ED%8F%B0-%EA%B5%AC%ED%98%95%EC%9D%B4%EB%9D%BC-%EB%94%94%EC%9E%90%EC%9D%B8%EA%B0%9C%EB%B0%A4%ED%8B%B0-%EC%BC%80%EC%9D%B4%EC%8A%A4%EB%B0%96%EC%97%90-2qutvg77"

    async with AsyncSession() as session:
        response = await session.get(url, impersonate="chrome120")
        html_content = response.text

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(java_script_enabled=False)
        page = await context.new_page()

        async def intercept_post(route):
            if route.request.resource_type == "script":
                await route.abort()
            elif route.request.url == url:
                await route.fulfill(body=html_content, content_type="text/html")
            else:
                await route.continue_()

        await page.route("**/*", intercept_post)
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(2)  # Wait for CSS

        dom = await page.content()
        with open("playwright_dom.html", "w", encoding="utf-8") as f:
            f.write(dom)
        print(f"Dumped DOM length: {len(dom)}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
