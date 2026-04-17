import asyncio
from unittest.mock import AsyncMock

async def main():
    try:
        title_el = AsyncMock()
        title_el.inner_text = AsyncMock(return_value="뽐뿌 할인!")

        content_el = AsyncMock()
        content_el.inner_text = AsyncMock(return_value="내용입니다.     이것은 10자 이상입니다.") # Length should be > 10 for ppomppu check!
        content_el.query_selector_all = AsyncMock(return_value=[])

        main_container_mock = AsyncMock()

        def qs_map(sel):
            if "h1" == sel:
                return title_el
            if ".board-contents" == sel:
                return content_el
            return main_container_mock

        page_mock = AsyncMock()
        page_mock.query_selector.side_effect = qs_map
        main_container_mock.query_selector.side_effect = lambda sel: content_el


        # Now simulate the scraper code
        # 1. title
        el = await page_mock.query_selector("h1")
        if el:
            text = (await el.inner_text()).strip()
            print("Title text:", repr(text))

        # 2. content
        main_container = await page_mock.query_selector(".board-contents")
        el = await main_container.query_selector(".board-contents")
        if el:
            print("el is:", type(el), el)
            inner_text_result = await el.inner_text()
            print("await el.inner_text() is:", type(inner_text_result), inner_text_result)
            text = inner_text_result.strip()
            print("text type:", type(text))
            print("Content text:", repr(text))
            if text and len(text) > 10:
                print("Len is > 10")

                img_elements = await el.query_selector_all("img")
                for img_el in img_elements:
                    src = await img_el.get_attribute("src")
                    print("Img:", src)

    except Exception:
        import traceback
        traceback.print_exc()

asyncio.run(main())
