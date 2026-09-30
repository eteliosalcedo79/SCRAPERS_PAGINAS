import asyncio
import json
from playwright.async_api import async_playwright

# URL de la página que vamos a scrapear
BASE_URL = "https://tarjetaroja.love/"
# Nombre del archivo JSON que se subirá automáticamente a GitHub
OUTPUT_FILE = "resultados.json"

async def main():
    results = {}

    async with async_playwright() as p:
        # Iniciamos el navegador en modo headless (sin interfaz gráfica)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Abriendo página principal...", flush=True)
        try:
            # Usamos networkidle para esperar a que carguen los scripts del acordeón
            await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error cargando la página principal: {e}", flush=True)
            await browser.close()
            return

        # --- Verificación de bloqueo por Cloudflare ---
        content = await page.content()
        if "Just a moment" in content or "cf-challenge" in content or "Cloudflare" in content:
            print("⚠️ ALERTA: GitHub Actions ha sido bloqueado por Cloudflare.", flush=True)
            print("Solución: Ejecuta el script localmente en tu PC o usa un Proxy Residencial.", flush=True)
            await browser.close()
            return
        # -----------------------------------------------

        print("Buscando eventos...", flush=True)
        try:
            await page.wait_for_selector("article.tr-event", timeout=20000)
        except Exception as e:
            print(f"No se encontraron eventos. Error: {e}", flush=True)
            await browser.close()
            return

        # Contamos cuántos eventos hay en total
        total_eventos = await page.locator("article.tr-event").count()
        print(f"Se encontraron {total_eventos} eventos en total.", flush=True)

        for i in range(total_eventos):
            # Re-consultamos el evento en cada iteración para evitar elementos obsoletos
            evento = page.locator("article.tr-event").nth(i)
            
            # Extraer el título del evento
            try:
                titulo_elem = evento.locator(".tr-event-title")
                if await titulo_elem.count() > 0:
                    titulo = (await titulo_elem.text_content()).strip()
                else:
                    titulo = f"Evento_{i+1}"
            except:
                titulo = f"Evento_{i+1}"

            print(f"\n[{i+1}/{total_eventos}] Procesando: {titulo}", flush=True)

            # Contamos cuántos canales tiene este evento específico
            canales_locator = evento.locator(".tr-event-channel")
            canales_count = await canales_locator.count()
            
            if canales_count == 0:
                print(f"  -> No se encontraron canales para este evento.", flush=True)
                continue

            results[titulo] = {}

            for j in range(canales_count):
                try:
                    # Re-consultamos el canal específico en cada iteración
                    canal = canales_locator.nth(j)
                    
                    # Esperamos a que el canal esté adjunto al DOM
                    await canal.wait_for(state="attached", timeout=5000)
                    
                    # Usamos text_content() para leer el nombre aunque esté oculto en el acordeón
                    nombre_canal = (await canal.text_content()).strip()
                    if not nombre_canal:
                        nombre_canal = f"Canal_{j+1}"
                        
                    url_canal = await canal.get_attribute("href")
                    if not url_canal.startswith("http"):
                        url_canal = BASE_URL.rstrip("/") + url_canal

                    print(f"  -> Procesando canal: {nombre_canal}", flush=True)

                    # Navegamos a la página del canal
                    await page.goto(url_canal, wait_until="domcontentloaded", timeout=30000)
                    
                    # Esperamos a que el iframe esté adjunto
                    await page.wait_for_selector("iframe", state="attached", timeout=10000)
                    
                    iframe = page.locator("iframe").first
                    src = await iframe.get_attribute("src")
                    
                    results[titulo][nombre_canal] = src
                    print(f"     - {nombre_canal}: OK", flush=True)

                    # Regresamos a la página principal para el siguiente canal
                    await page.go_back(wait_until="domcontentloaded")
                    # Esperamos a que los eventos se vuelvan a cargar
                    await page.wait_for_selector("article.tr-event", timeout=10000)

                except Exception as e:
                    print(f"     - Error con {nombre_canal}: {e}", flush=True)
                    results[titulo][nombre_canal] = None
                    
                    # Si hay un error, intentamos volver a la página principal para no quedar atascados
                    try:
                        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_selector("article.tr-event", timeout=10000)
                    except:
                        pass

        await browser.close()

    # Guardamos los resultados en el archivo JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Datos guardados en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
