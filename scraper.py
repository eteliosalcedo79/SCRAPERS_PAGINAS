import asyncio
import json
from playwright.async_api import async_playwright

URL = "https://pirlotvapp.pro/"
SITE_ROOT = "https://pirlotvapp.pro"
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
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"Error cargando página: {e}", flush=True)
            await browser.close()
            return

        await page.wait_for_timeout(5000)

        # 1. OBTENER LISTA DE TÍTULOS (Evita errores si la página se actualiza)
        botones_eventos = page.locator("button.ag-toggle")
        total_eventos = await botones_eventos.count()
        print(f"Se encontraron {total_eventos} eventos.", flush=True)

        titulos_eventos = []
        for i in range(total_eventos):
            try:
                texto = await botones_eventos.nth(i).locator("span.font-semibold").inner_text()
                titulos_eventos.append(texto.strip())
            except:
                pass

        for i, titulo in enumerate(titulos_eventos):
            print(f"\n[{i+1}/{len(titulos_eventos)}] Abriendo evento: {titulo}", flush=True)
            
            try:
                # Buscamos el evento exacto por su título
                evento_li = page.locator("li", has_text=titulo).first
                
                # Hacemos clic en el acordeón
                await evento_li.locator("button.ag-toggle").click()
                await page.wait_for_timeout(2500)

                results[titulo] = {}

                # 2. BUSCAR CANALES (Solo dentro de este evento)
                # Buscamos los botones que estén dentro de este <li>
                canales = evento_li.locator("button, a").filter(has_text="Español")
                total_canales = await canales.count()
                print(f"  -> Canales encontrados en este evento: {total_canales}", flush=True)

                for j in range(total_canales):
                    try:
                        canal_elem = canales.nth(j)
                        
                        # 3. LIMPIAR EL NOMBRE DEL CANAL (Quitar la flechita ▶)
                        nombre_canal = await canal_elem.inner_text()
                        nombre_canal = nombre_canal.replace("▶", "").strip().replace("\n", " ")
                        
                        if len(nombre_canal) < 3 or "vs" in nombre_canal: 
                            continue

                        print(f"     -> Abriendo canal: {nombre_canal}", flush=True)
                        
                        await canal_elem.click(force=True) 
                        await page.wait_for_timeout(4000)

                        # 4. EXTRAER Y COMPLETAR LA URL
                        iframe = page.locator("iframe").first
                        if await iframe.count() > 0:
                            src = await iframe.get_attribute("src")
                            if src:
                                # Si el enlace empieza con "/", le agregamos el dominio
                                if src.startswith("/"):
                                    src = SITE_ROOT + src
                                results[titulo][nombre_canal] = src
                                print(f"     ✅ {src}", flush=True)
                            else:
                                results[titulo][nombre_canal] = None
                        else:
                            print("     ❌ No se encontró iframe", flush=True)
                            results[titulo][nombre_canal] = None

                        # 5. CERRAR EL MODAL A LA FUERZA
                        # Intentamos con Escape
                        await page.keyboard.press("Escape") 
                        await page.wait_for_timeout(1000)
                        
                        # Si el iframe sigue ahí, significa que el modal no se cerró.
                        # Buscamos el botón de la "X" y le damos clic.
                        if await page.locator("iframe").count() > 0:
                            try:
                                # Buscamos cualquier botón que diga "×", "X" o tenga la clase close
                                cerrar = page.locator("button", has_text="×").or_(page.locator("button", has_text="X")).or_(page.locator(".close-btn")).first
                                await cerrar.click(timeout=3000)
                            except:
                                # Si de plano no encuentra cómo cerrar, recarga la página (a prueba de balas)
                                print("     (Forzando recarga para cerrar modal)", flush=True)
                                await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
                                await page.wait_for_timeout(3000)
                                await page.locator("li", has_text=titulo).first.locator("button.ag-toggle").click()
                                await page.wait_for_timeout(2000)

                    except Exception as e:
                        print(f"     ⚠️ Error al abrir canal: {e}", flush=True)

                # Al terminar con los canales, cerramos el acordeón (si no se recargó la página)
                if await page.locator("iframe").count() == 0:
                    await evento_li.locator("button.ag-toggle").click()
                    await page.wait_for_timeout(1000)

            except Exception as e:
                print(f"  ⚠️ Error con el evento: {e}", flush=True)

        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Guardado en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
