import asyncio
import json
from playwright.async_api import async_playwright

URL = "https://pirlotvapp.pro/"
OUTPUT_FILE = "resultados.json"

async def main():
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        print("🌐 Abriendo pirlotvapp...", flush=True)
        try:
            await page.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error cargando página: {e}", flush=True)
            await browser.close()
            return

        # Guardar HTML inicial por si falla
        with open("debug_0_inicio.html", "w", encoding="utf-8") as f:
            f.write(await page.content())

        await page.wait_for_timeout(4000)

        # 1. Encontrar los eventos (buscando el texto " vs ")
        locators_eventos = page.locator("text=/ vs /i")
        total_eventos = await locators_eventos.count()
        print(f"Se encontraron {total_eventos} posibles eventos.", flush=True)

        # Recolectamos los textos para evitar problemas de "elementos obsoletos" (stale)
        textos_eventos = []
        for i in range(total_eventos):
            try:
                texto = await locators_eventos.nth(i).inner_text()
                if texto.strip() not in textos_eventos:
                    textos_eventos.append(texto.strip())
            except:
                pass

        for i, titulo_ev in enumerate(textos_eventos):
            print(f"\n[{i+1}/{len(textos_eventos)}] Abriendo evento: {titulo_ev}", flush=True)
            
            try:
                # Clic en el evento para abrir el acordeón
                await page.get_by_text(titulo_ev, exact=False).first.click(timeout=5000)
                await page.wait_for_timeout(2000) # Esperar que se despliegue

                # Guardar HTML del acordeón (por si no encuentra canales)
                with open(f"debug_evento_{i+1}.html", "w", encoding="utf-8") as f:
                    f.write(await page.content())

                results[titulo_ev] = {}

                # 2. Buscar los canales dentro del acordeón abierto
                # Buscamos botones o enlaces comunes que aparecen en tu captura
                canales = page.locator("text=ESPN, text=Español, text=Disney, text=Movil, text=MX")
                if await canales.count() == 0:
                    canales = page.locator("a:visible, button:visible") # Fallback

                total_canales = await canales.count()
                print(f"  -> Canales encontrados: {total_canales}", flush=True)

                for j in range(total_canales):
                    try:
                        canal_elem = canales.nth(j)
                        nombre_canal = await canal_elem.inner_text()
                        
                        # Evitar clics en cosas que no son canales
                        if len(nombre_canal.strip()) < 2 or "×" in nombre_canal:
                            continue

                        print(f"     Haciendo clic en canal: {nombre_canal.strip()}", flush=True)
                        
                        # 3. Clic en el canal para abrir el modal
                        await canal_elem.click(timeout=5000)
                        await page.wait_for_timeout(3000) # Esperar que cargue el iframe

                        # Guardar HTML del modal
                        with open(f"debug_modal_{i+1}_{j+1}.html", "w", encoding="utf-8") as f:
                            f.write(await page.content())

                        # Extraer src del iframe
                        iframe = page.locator("iframe").first
                        if await iframe.count() > 0:
                            src = await iframe.get_attribute("src")
                            results[titulo_ev][nombre_canal.strip()] = src
                            print(f"     ✅ {src}", flush=True)
                        else:
                            print("     ❌ No se encontró iframe", flush=True)
                            results[titulo_ev][nombre_canal.strip()] = None

                        # 4. Cerrar el modal para poder hacer clic en el siguiente canal
                        await page.keyboard.press("Escape")
                        await page.wait_for_timeout(1000)
                        
                        # Intentar clic en la "X" por si Escape no funciona
                        try:
                            cerrar = page.locator("button:has-text('×'), button[class*='close'], .close").first
                            if await cerrar.is_visible():
                                await cerrar.click()
                                await page.wait_for_timeout(1000)
                        except:
                            pass

                    except Exception as e:
                        print(f"     ⚠️ Error en canal: {e}", flush=True)
                        await page.keyboard.press("Escape")
                        await page.wait_for_timeout(1000)

            except Exception as e:
                print(f"  ⚠️ Error con el evento: {e}", flush=True)

        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Guardado en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
