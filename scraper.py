import asyncio
import json
from playwright.async_api import async_playwright

BASE_URL = "https://pelisjuanita.com/tv/fox-sports"
OUTPUT_FILE = "resultados_pelisjuanita.json"

async def main():
    resultados = {"FOX SPORTS": {}} # Nombre del canal

    async with async_playwright() as p:
        # IMPORTANTE: headless=True es obligatorio para GitHub Actions
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 900},
            locale="es-ES",
        )
        
        # Ocultar que somos un bot
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = await context.new_page()

        print(f"Abriendo {BASE_URL} ...", flush=True)
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000) # Esperar a que cargue el JS
        except Exception as e:
            print(f"Error al cargar: {e}", flush=True)
            await browser.close()
            return

        # Buscar todos los elementos que digan "Servidor" (botones o pestañas)
        # Playwright buscará cualquier elemento con ese texto.
        print("Buscando botones de servidores...", flush=True)
        
        # Localizamos los botones por texto
        servidores = page.locator("text=/Servidor \\d+/i")
        count = await servidores.count()
        
        if count == 0:
            print("⚠️ No se encontraron botones de servidor.", flush=True)
        else:
            print(f"✅ Se encontraron {count} servidores.", flush=True)

        for i in range(count):
            servidor = servidores.nth(i)
            nombre_servidor = await servidor.inner_text()
            nombre_servidor = nombre_servidor.strip()
            print(f"  -> Probando: {nombre_servidor}", flush=True)

            try:
                await servidor.click()
                # Esperar un poco a que el iframe se actualice
                await page.wait_for_timeout(3000) 
                
                # Buscar el iframe en la página
                iframe = page.locator("iframe").first
                src = await iframe.get_attribute("src")
                
                if src:
                    resultados["FOX SPORTS"][nombre_servidor] = src
                    print(f"     ✅ {src}", flush=True)
                else:
                    print("     ❌ Iframe sin src", flush=True)
                    resultados["FOX SPORTS"][nombre_servidor] = None
            except Exception as e:
                print(f"     ⚠️ Error al clicar: {e}", flush=True)
                resultados["FOX SPORTS"][nombre_servidor] = None

        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Guardado en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
