import asyncio

from playwright.async_api import async_playwright


async def probe(headless: bool):
    print(f"=== headless={headless} ===", flush=True)
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=headless)
            page = await browser.new_page()
            response = await page.goto(
                "https://book.douban.com/subject/1007305/",
                wait_until="domcontentloaded",
                timeout=20000,
            )
            print("status", response.status if response else None, flush=True)
            print("title", await page.title(), flush=True)
            print("url", page.url, flush=True)
            print("interest_count", await page.locator("#interest_sectl").count(), flush=True)
            await browser.close()
    except Exception as exc:
        print("ERROR", repr(exc), flush=True)


async def main():
    await probe(False)
    await probe(True)


if __name__ == "__main__":
    asyncio.run(main())
