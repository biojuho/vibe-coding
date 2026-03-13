import asyncio
from playwright.async_api import async_playwright
from curl_cffi.requests import AsyncSession

async def main():
    url = "https://www.teamblind.com/kr/post/%ED%98%95%EB%93%A4-%EB%82%98-%EC%9D%B8%ED%85%8C%EB%A6%AC%EC%96%B4-%EA%B3%B5%EC%82%AC-%EC%A4%91%EC%9D%B8%EB%8D%B0-guyg5nxl"
    
    # 1. Fetch HTML with curl_cffi
    async with AsyncSession() as session:
        response = await session.get(url, impersonate="chrome120")
        html_content = response.text
        
        # Inject <base> tag to fix relative links for CSS/Images
        base_tag = '<base href="https://www.teamblind.com/">'
        html_content = html_content.replace('<head>', f'<head>{base_tag}')
        
    print("HTML fetched, length:", len(html_content))
    
    # 2. Render with Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # Wait for network idle might fail if some resources 404, so we just wait load
        await page.set_content(html_content, wait_until="networkidle")
        await asyncio.sleep(2)
        
        await page.screenshot(path="test_injected.png", full_page=True)
        print("Saved test_injected.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
