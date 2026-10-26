import asyncio
from playwright.async_api import async_playwright

SITE_ROOT = "https://deporflix.pe"

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

        print("Abriendo página...", flush=True)
        try:
            await page.goto(SITE_ROOT, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error al cargar: {e}")

        print("Esperando 5 segundos extra para que cargue el JS...", flush=True)
        await page.wait_for_timeout(5000)
        
        # Hacemos scroll hasta abajo para forzar la carga de los canales si es "lazy loading"
        print("Haciendo scroll...", flush=True)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(3000) # Esperar a que carguen al hacer scroll

        # Guardar el HTML
        html_content = await page.content()
        with open("debug_pagina.html", "w", encoding="utf-8") as f:
            f.write(html_content)
            
        # Guardar una captura de pantalla completa
        await page.screenshot(path="debug_pantalla.png", full_page=True)
        
        print("✅ Archivos de depuración guardados: debug_pagina.html y debug_pantalla.png", flush=True)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
