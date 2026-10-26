import asyncio
from playwright.async_api import async_playwright

URL = "https://pirlotvapp.pro/"

async def main():
    async with async_playwright() as p:
        # En GitHub Actions SIEMPRE debe ser headless=True
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        print("🌐 Abriendo la página...", flush=True)
        try:
            await page.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error al cargar: {e}")
            await browser.close()
            return

        await page.wait_for_timeout(4000)
        
        # 1. Guardar HTML inicial y captura
        html_inicial = await page.content()
        with open("1_principal.html", "w", encoding="utf-8") as f:
            f.write(html_inicial)
        await page.screenshot(path="1_principal.png")
        print("✅ Guardado: 1_principal.html")

        # 2. Clic en el primer evento
        print("🖱️ Intentando clic en el primer evento...", flush=True)
        try:
            # Buscamos el texto del partido que sale en tu captura
            primer_evento = page.locator("text=Al-Qadisiyah").first
            if await primer_evento.count() == 0:
                primer_evento = page.locator("text=ESPN").first
            
            await primer_evento.click(timeout=10000)
            await page.wait_for_timeout(3000) 
            
            html_acordeon = await page.content()
            with open("2_acordeon.html", "w", encoding="utf-8") as f:
                f.write(html_acordeon)
            await page.screenshot(path="2_acordeon.png")
            print("✅ Guardado: 2_acordeon.html")
            
        except Exception as e:
            print(f"⚠️ No se pudo hacer clic en el evento: {e}")

        # 3. Clic en el primer canal
        print("🖱️ Intentando clic en el primer canal...", flush=True)
        try:
            primer_canal = page.locator("text=ESPN").first
            if await primer_canal.count() == 0:
                primer_canal = page.locator("text=Español").first

            await primer_canal.click(timeout=10000)
            await page.wait_for_timeout(4000) 
            
            html_modal = await page.content()
            with open("3_modal.html", "w", encoding="utf-8") as f:
                f.write(html_modal)
            await page.screenshot(path="3_modal.png")
            print("✅ Guardado: 3_modal.html")
            
        except Exception as e:
            print(f"⚠️ No se pudo hacer clic en el canal: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
