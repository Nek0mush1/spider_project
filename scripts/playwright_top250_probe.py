import asyncio

from playwright.async_api import async_playwright
from playwright_stealth import Stealth


URLS = [
    "https://book.douban.com/top250?start=75",
    "https://book.douban.com/top250?start=100",
]


async def main():
    stealth = Stealth()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page()
        await stealth.apply_stealth_async(page)
        for url in URLS:
            print(f"=== {url} ===", flush=True)
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(3000)
                print("status", response.status if response else None, flush=True)
                print("title", await page.title(), flush=True)
                print("final_url", page.url, flush=True)
                print("items", await page.locator("tr.item").count(), flush=True)
                print("login_links", await page.locator(".nav-login").count(), flush=True)
            except Exception as exc:
                print("ERROR", repr(exc), flush=True)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
