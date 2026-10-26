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
        page.set_default_timeout(8000)

        print("🌐 Abriendo pirlotvapp...", flush=True)
        try:
            await page.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error cargando página: {e}", flush=True)
            await browser.close()
            return

        await page.wait_for_timeout(4000)

        # 1. LOCALIZAR LOS EVENTOS (Buscamos los <li> que contienen el botón del partido)
        eventos = page.locator("li:has(button.ag-toggle)")
        total_eventos = await eventos.count()
        print(f"Se encontraron {total_eventos} eventos.", flush=True)

        for i in range(total_eventos):
            try:
                # Seleccionamos el evento actual (la caja fuerte)
                evento_actual = eventos.nth(i)
                titulo = await evento_actual.locator("span.font-semibold").inner_text()
                titulo = titulo.strip()
                
                print(f"\n[{i+1}/{total_eventos}] Abriendo evento: {titulo}", flush=True)

                # Hacemos clic para desplegar el acordeón
                await evento_actual.locator("button.ag-toggle").click()
                await page.wait_for_timeout(2000)

                results[titulo] = {}

                # 2. BUSCAR CANALES (¡SOLO DENTRO DEL EVENTO ACTUAL!)
                # Buscamos elementos clickeables dentro de este <li> específico
                canales = evento_actual.locator("button, a").filter(has_text="Español")
                
                # Si no encuentra "Español", buscamos cualquier botón dentro del evento que no sea el de abrir/cerrar
                if await canales.count() == 0:
                    canales = evento_actual.locator("button, a").filter(has_not_text="▾").filter(has_not_text="▴")

                total_canales = await canales.count()
                print(f"  -> Canales encontrados en este evento: {total_canales}", flush=True)

                for j in range(total_canales):
                    try:
                        canal_elem = canales.nth(j)
                        nombre_canal = await canal_elem.inner_text()
                        nombre_canal = nombre_canal.strip().replace("\n", " ")
                        
                        # Evitar clics accidentales en botones vacíos o el título del partido
                        if len(nombre_canal) < 3 or "vs" in nombre_canal: 
                            continue

                        print(f"     -> Abriendo canal: {nombre_canal}", flush=True)
                        
                        # 3. CLIC EN EL CANAL (Abre el modal)
                        await canal_elem.click(force=True) 
                        await page.wait_for_timeout(4000) # Esperar a que cargue el iframe

                        # 4. EXTRAER EL SRC DEL IFRAME (El modal se abre en el body, así que buscamos global)
                        iframe = page.locator("iframe").first
                        if await iframe.count() > 0:
                            src = await iframe.get_attribute("src")
                            results[titulo][nombre_canal] = src
                            print(f"     ✅ {src}", flush=True)
                        else:
                            print("     ❌ No se encontró iframe", flush=True)
                            results[titulo][nombre_canal] = None

                        # 5. CERRAR EL MODAL
                        await page.keyboard.press("Escape") 
                        await page.wait_for_timeout(1000)
                        
                        cerrar = page.locator("button:has-text('×'), button:has-text('X'), .close").first
                        if await cerrar.is_visible():
                            await cerrar.click()
                            await page.wait_for_timeout(1000)

                    except Exception as e:
                        print(f"     ⚠️ Error al abrir canal: {e}", flush=True)
                        await page.keyboard.press("Escape")
                        await page.wait_for_timeout(1000)

                # Volver a hacer clic en el evento para cerrar el acordeón
                await evento_actual.locator("button.ag-toggle").click()
                await page.wait_for_timeout(1000)

            except Exception as e:
                print(f"  ⚠️ Error con el evento: {e}", flush=True)

        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Guardado en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
