import asyncio
import json
from playwright.async_api import async_playwright

BASE_URL = "https://tarjetaroja.love/"
OUTPUT_FILE = "canales_tarjetaroja.json"

async def main():
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Abriendo página principal...", flush=True)
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)

        # Esperamos a que se carguen los eventos
        print("Buscando eventos...", flush=True)
        try:
            await page.wait_for_selector("article.tr-event", timeout=20000)
        except Exception as e:
            print(f"No se encontraron eventos. Error: {e}", flush=True)
            await browser.close()
            return

        # Extraemos todos los eventos de una sola vez
        eventos = await page.locator("article.tr-event").all()
        total_eventos = len(eventos)
        print(f"Se encontraron {total_eventos} eventos en total.", flush=True)

        for i, evento in enumerate(eventos):
            # Extraer el título del evento
            try:
                titulo = (await evento.locator(".tr-event-title").inner_text()).strip()
            except:
                titulo = f"Evento_{i+1}"

            print(f"\n[{i+1}/{total_eventos}] Procesando: {titulo}", flush=True)

            # Extraer los enlaces de los canales de este evento
            canales = await evento.locator(".tr-event-channel").all()
            if not canales:
                print(f"  -> No se encontraron canales para este evento.", flush=True)
                continue

            results[titulo] = {}

            for canal in canales:
                nombre_canal = (await canal.inner_text()).strip()
                url_canal = await canal.get_attribute("href")
                if not url_canal.startswith("http"):
                    url_canal = BASE_URL.rstrip("/") + url_canal

                print(f"  -> Procesando canal: {nombre_canal}", flush=True)

                try:
                    # Navegamos a la página del canal para obtener el iframe
                    await page.goto(url_canal, wait_until="domcontentloaded", timeout=30000)
                    
                    # Esperamos a que aparezca el iframe
                    await page.wait_for_selector("iframe", timeout=10000)
                    
                    iframe = page.locator("iframe").first
                    src = await iframe.get_attribute("src")
                    
                    results[titulo][nombre_canal] = src
                    print(f"     - {nombre_canal}: OK", flush=True)
                except Exception as e:
                    print(f"     - Error con {nombre_canal}: {e}", flush=True)
                    results[titulo][nombre_canal] = None
                
                # Pequeña pausa para no saturar el servidor
                await page.wait_for_timeout(1000)

        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Datos guardados en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
