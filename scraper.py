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
            # AQUÍ ESTÁ EL CAMBIO: "domcontentloaded" en vez de "networkidle"
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"Error cargando página: {e}", flush=True)
            await browser.close()
            return

        # Le damos 5 segundos extra para que cargue el JS de los partidos
        await page.wait_for_timeout(5000)

        # 1. LOCALIZAR LOS EVENTOS
        eventos = page.locator("li:has(button.ag-toggle)")
        total_eventos = await eventos.count()
        print(f"Se encontraron {total_eventos} eventos.", flush=True)

        for i in range(total_eventos):
            try:
                evento_actual = eventos.nth(i)
                titulo = await evento_actual.locator("span.font-semibold").inner_text()
                titulo = titulo.strip()
                
                print(f"\n[{i+1}/{total_eventos}] Abriendo evento: {titulo}", flush=True)

                # Clic para abrir acordeón
                await evento_actual.locator("button.ag-toggle").click()
                await page.wait_for_timeout(2000)

                results[titulo] = {}

                # 2. BUSCAR CANALES (DENTRO DEL EVENTO)
                canales = evento_actual.locator("button, a").filter(has_text="Español")
                
                if await canales.count() == 0:
                    canales = evento_actual.locator("button, a").filter(has_not_text="▾").filter(has_not_text="▴")

                total_canales = await canales.count()
                print(f"  -> Canales encontrados en este evento: {total_canales}", flush=True)

                for j in range(total_canales):
                    try:
                        canal_elem = canales.nth(j)
                        nombre_canal = await canal_elem.inner_text()
                        nombre_canal = nombre_canal.strip().replace("\n", " ")
                        
                        if len(nombre_canal) < 3 or "vs" in nombre_canal: 
                            continue

                        print(f"     -> Abriendo canal: {nombre_canal}", flush=True)
                        
                        # Clic en canal
                        await canal_elem.click(force=True) 
                        await page.wait_for_timeout(4000)

                        # Extraer iframe
                        iframe = page.locator("iframe").first
                        if await iframe.count() > 0:
                            src = await iframe.get_attribute("src")
                            results[titulo][nombre_canal] = src
                            print(f"     ✅ {src}", flush=True)
                        else:
                            print("     ❌ No se encontró iframe", flush=True)
                            results[titulo][nombre_canal] = None

                        # Cerrar modal
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

                # Cerrar acordeón
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
