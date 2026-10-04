import asyncio
from playwright.async_api import async_playwright

BASE_URL = "https://futbol-libre.app/agenda"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
        )
        page = await context.new_page()
        await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(12000)

        # 1) HTML de un evento concreto
        snippet = await page.evaluate("""
            () => {
                const all = [...document.querySelectorAll('*')];
                const target = all.find(el =>
                    el.children.length > 0 &&
                    el.textContent.includes('Azerbaiyán') &&
                    el.textContent.includes('Lituania') &&
                    el.textContent.length < 400
                );
                if (!target) return 'NO ENCONTRADO';
                let node = target;
                for (let i = 0; i < 6 && node.parentElement; i++) {
                    if (node.className && typeof node.className === 'string' &&
                        (node.className.includes('event') || node.className.includes('match'))) {
                        return node.outerHTML.slice(0, 4000);
                    }
                    node = node.parentElement;
                }
                return node.outerHTML.slice(0, 4000);
            }
        """)
        print("===== EVENTO (fragmento HTML) =====", flush=True)
        print(snippet, flush=True)
        print("===== FIN EVENTO =====", flush=True)

        # 2) Iframes en agenda
        iframe_info = await page.evaluate("""
            () => [...document.querySelectorAll('iframe')].map(f => f.src).slice(0,5)
        """)
        print(f"IFRAMES en agenda: {iframe_info}", flush=True)

        with open("debug_agenda.html", "w", encoding="utf-8") as f:
            f.write(await page.content())
        await page.screenshot(path="debug_agenda.png", full_page=True)
        print("✅ debug_agenda.html y .png guardados", flush=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
