from curl_cffi.requests import AsyncSession
import asyncio

async def main():
    url = "https://www.teamblind.com/kr/post/%ED%98%95%EB%93%A4-%EB%82%98-%EC%9D%B8%ED%85%8C%EB%A6%AC%EC%96%B4-%EA%B3%B5%EC%82%AC-%EC%A4%91%EC%9D%B8%EB%8D%B0-guyg5nxl"
    async with AsyncSession() as session:
        response = await session.get(url, impersonate="chrome120")
        with open("raw2.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Saved raw2.html")

if __name__ == "__main__":
    asyncio.run(main())
