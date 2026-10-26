import asyncio
from playwright.async_api import async_playwright

AGENDA_URL = "https://pelotalibre.biz/agenda"

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

        print("Abriendo agenda de Pelota Libre...", flush=True)
        try:
            await page.goto(AGENDA_URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000) # Espera extra para JS
        except Exception as e:
            print(f"Error al cargar: {e}")

        print("Intentando abrir el primer partido (acordeón)...", flush=True)
        try:
            # Buscamos el primer elemento que tenga el texto 'vs' y le damos clic
            # Usamos force=True por si hay algún elemento invisible encima
            primer_partido = page.locator("text=vs").first
            await primer_partido.click(force=True)
            await page.wait_for_timeout(2000) # Esperar a que se despliegue el acordeón
            print("Clic realizado con éxito.")
        except Exception as e:
            print(f"No se pudo hacer clic en el partido: {e}")

        # Guardar el HTML
        html_content = await page.content()
        with open("debug_agenda.html", "w", encoding="utf-8") as f:
            f.write(html_content)
            
        # Guardar captura de pantalla
        await page.screenshot(path="debug_agenda.png", full_page=True)
        
        print("✅ Archivos guardados: debug_agenda.html y debug_agenda.png", flush=True)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
