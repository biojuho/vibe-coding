import json
import asyncio
from curl_cffi.requests import AsyncSession

async def main():
    url = "https://www.teamblind.com/kr/post/%EB%82%B4-%ED%8F%B0-%EA%B5%AC%ED%98%95%EC%9D%B4%EB%9D%BC-%EB%94%94%EC%9E%90%EC%9D%B8%EA%B0%9C%EB%B0%A4%ED%8B%B0-%EC%BC%80%EC%9D%B4%EC%8A%A4%EB%B0%96%EC%97%90-2qutvg77"
    cookies = {}
    try:
        with open(".auth/state.json", "r") as f:
            state = json.load(f)
            for cookie in state.get("cookies", []):
                cookies[cookie["name"]] = cookie["value"]
    except Exception as e:
        print("Failed to load cookies:", e)
        return

    async with AsyncSession(cookies=cookies) as session:
        response = await session.get(url, impersonate="chrome120")
        if "article-wrap" in response.text:
            print("SUCCESS! Found article-wrap WITH cookies!")
        else:
            print("STILL FAILED... The post might be deleted or cookies insufficient.")
            # Lets see what the title is
            import re
            title = re.search(r'<title>(.*?)</title>', response.text)
            print("Title:", title.group(1) if title else "No title")

if __name__ == "__main__":
    asyncio.run(main())
