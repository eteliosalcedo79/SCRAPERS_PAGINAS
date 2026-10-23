import asyncio
import json
from playwright.async_api import async_playwright

BASE_URL = "https://pelisjuanita.com/tv/fox-sports"
OUTPUT_FILE = "resultados_pelisjuanita.json"

async def main():
    resultados = {"FOX SPORTS": {}}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900}
        )
        page = await context.new_page()

        print(f"Abriendo {BASE_URL} ...", flush=True)
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            
            # --- INICIO DE SESIÓN AUTOMÁTICO ---
            try:
                await page.wait_for_selector('input[name="apodo"]', timeout=5000)
                print("🔒 Pantalla de acceso detectada. Ingresando apodo 'etelio'...", flush=True)
                
                # Escribimos tu apodo
                await page.fill('input[name="apodo"]', 'etelio')
                # Hacemos clic en el botón de Aceptar y Continuar
                await page.click('button[type="submit"]')
                
                # Esperamos a que cargue la página tras el login
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(3000)
                print("✅ Sesión iniciada.", flush=True)
                
                # Si después del login no nos lleva al canal, volvemos a ir
                if "fox-sports" not in page.url:
                    print("Navegando a la página del canal...", flush=True)
                    await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(3000)
            except Exception:
                print("ℹ️ No se requirió login (o ya estamos dentro).", flush=True)
            # --- FIN DE SESIÓN AUTOMÁTICA ---

            # Guardar el HTML para ver cómo es la página ya logueados
            html = await page.content()
            with open("debug_pagina.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("✅ HTML guardado en debug_pagina.html", flush=True)

            # Buscar los iframes
            iframes = page.locator("iframe")
            count = await iframes.count()
            print(f"Se encontraron {count} iframes en la página.", flush=True)

            for i in range(count):
                src = await iframes.nth(i).get_attribute("src")
                if src:
                    nombre = f"Reproductor_{i+1}"
                    print(f"✅ {nombre}: {src}", flush=True)
                    resultados["FOX SPORTS"][nombre] = src

        except Exception as e:
            print(f"Error durante la ejecución: {e}", flush=True)
        finally:
            await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Guardado en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
