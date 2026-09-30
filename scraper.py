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
        try:
            # Usamos networkidle para esperar a que carguen los scripts que arman el acordeón
            await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error cargando la página principal: {e}", flush=True)
            await browser.close()
            return

        print("Buscando eventos...", flush=True)
        try:
            await page.wait_for_selector("article.tr-event", timeout=20000)
        except Exception as e:
            print(f"No se encontraron eventos. Error: {e}", flush=True)
            await browser.close()
            return

        # Extraemos todos los eventos
        eventos = await page.locator("article.tr-event").all()
        total_eventos = len(eventos)
        print(f"Se encontraron {total_eventos} eventos en total.", flush=True)

        for i, evento in enumerate(eventos):
            # Extraer el título del evento (usando text_content para evitar problemas de visibilidad)
            try:
                titulo = (await evento.locator(".tr-event-title").text_content()).strip()
                if not titulo:
                    titulo = f"Evento_{i+1}"
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
                try:
                    # Usamos text_content() en lugar de inner_text()
                    nombre_canal = (await canal.text_content()).strip()
                    if not nombre_canal:
                        nombre_canal = "Canal_Desconocido"
                        
                    url_canal = await canal.get_attribute("href")
                    if not url_canal.startswith("http"):
                        url_canal = BASE_URL.rstrip("/") + url_canal

                    print(f"  -> Procesando canal: {nombre_canal}", flush=True)

                    # Navegamos a la página del canal
                    await page.goto(url_canal, wait_until="domcontentloaded", timeout=30000)
                    
                    # Esperamos a que el iframe esté adjunto en el DOM
                    await page.wait_for_selector("iframe", state="attached", timeout=10000)
                    
                    iframe = page.locator("iframe").first
                    src = await iframe.get_attribute("src")
                    
                    results[titulo][nombre_canal] = src
                    print(f"     - {nombre_canal}: OK", flush=True)
                except Exception as e:
                    print(f"     - Error con {nombre_canal}: {e}", flush=True)
                    results[titulo][nombre_canal] = None
                
                # Pausa breve entre canales
                await page.wait_for_timeout(1000)

        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Datos guardados en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
