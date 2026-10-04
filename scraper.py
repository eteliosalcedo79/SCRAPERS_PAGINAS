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
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        print("Navegando...", flush=True)
        await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)

        print("Esperando 15 s para JS...", flush=True)
        await page.wait_for_timeout(15000)

        title = await page.title()
        print(f"TITLE: {title}", flush=True)

        body_text = (await page.locator("body").inner_text())[:600]
        print("---- BODY TEXT (primeros 600 chars) ----", flush=True)
        print(body_text, flush=True)
        print("---- FIN BODY ----", flush=True)

        for sel in ["article", "li", ".event", ".match", "a", "div[class]",
                    "[class*='event']", "[class*='match']", "[class*='partido']"]:
            try:
                n = await page.locator(sel).count()
                print(f"  '{sel}' → {n}", flush=True)
            except Exception as e:
                print(f"  '{sel}' → error: {e}", flush=True)

        # Guardar HTML completo
        with open("debug_agenda.html", "w", encoding="utf-8") as f:
            f.write(await page.content())
        print("✅ debug_agenda.html guardado", flush=True)

        # Guardar screenshot para ver visualmente qué cargó
        await page.screenshot(path="debug_agenda.png", full_page=True)
        print("✅ debug_agenda.png guardado", flush=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
