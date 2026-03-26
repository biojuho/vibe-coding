from curl_cffi.requests import AsyncSession
import asyncio
from bs4 import BeautifulSoup

async def main():
    url = "https://www.teamblind.com/kr/post/%ED%98%95%EB%93%A4-%EB%82%98-%EC%9D%B8%ED%85%8C%EB%A6%AC%EC%96%B4-%EA%B3%B5%EC%82%AC-%EC%A4%91%EC%9D%B8%EB%8D%B0-guyg5nxl"
    async with AsyncSession() as session:
        response = await session.get(url, impersonate="chrome120")
        html = response.text

        soup = BeautifulSoup(html, "html.parser")

        # Look for the title text exactly
        print("Looking for Title...")
        for tag in soup.find_all(string=lambda t: t and "인테리어 공사 중인데" in t):
            parent = tag.parent
            print("Found exact text in tag:", parent.name)
            print("Classes:", parent.get("class"))

            # Print ancestors' classes
            ancestor = parent.parent
            for i in range(5):
                if ancestor and ancestor.name != "[document]":
                    print(f"Ancestor {i+1} ({ancestor.name}):", ancestor.get("class"))
                    ancestor = ancestor.parent

if __name__ == "__main__":
    asyncio.run(main())
