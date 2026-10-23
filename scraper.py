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
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox", 
                "--disable-dev-shm-usage",
                "--disable-web-security"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="es-ES"
        )
        
        # Camuflaje: Ocultar que somos un bot
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        
        page = await context.new_page()

        print(f"Abriendo {BASE_URL} ...", flush=True)
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            
            # Esperamos hasta 20 segundos a que Cloudflare nos deje pasar y aparezca el login
            print("Esperando a que Cloudflare nos deje pasar...", flush=True)
            try:
                await page.wait_for_selector('input[name="apodo"]', timeout=20000)
                
                print("🔒 Ingresando apodo 'etelio'...", flush=True)
                await page.fill('input[name="apodo"]', 'etelio')
                await page.click('button[type="submit"]')
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(3000)
                print("✅ Sesión iniciada.", flush=True)
                
                if "fox-sports" not in page.url:
                    await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(3000)
                    
            except Exception as e:
                print("⚠️ Cloudflare nos bloqueó o el login cambió.", flush=True)

            # Guardamos HTML por si acaso
            html = await page.content()
            with open("debug_pagina.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("✅ HTML guardado en debug_pagina.html", flush=True)

            # Buscar iframes
            iframes = page.locator("iframe")
            count = await iframes.count()
            print(f"Se encontraron {count} iframes en la página.", flush=True)

            for i in range(count):
                src = await iframes.nth(i).get_attribute("src")
                if src:
                    nombre = f"Reproductor_{i+1}"
                    resultados["FOX SPORTS"][nombre] = src

        except Exception as e:
            print(f"Error: {e}", flush=True)
        finally:
            await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())
