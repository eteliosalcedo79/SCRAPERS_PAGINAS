import asyncio
import json
import re
from playwright.async_api import async_playwright

PELICULA_URL = "https://ganovideo.com/peliculas/hope-el-primer-impacto/"
OUTPUT_FILE = "resultados_ganovideo.json"

async def main():
    results = {}
    
    async with async_playwright() as p:
        # Configuramos un navegador más "real" para evitar bloqueos
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        
        print(f"Abriendo: {PELICULA_URL}", flush=True)
        
        try:
            # Esperamos a que la red se calme
            await page.goto(PELICULA_URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000) # Pausa extra por si hay JS pesado

            # Buscamos CUALQUIER elemento que contenga la palabra Película o Trailer (ignorando tildes/mayúsculas)
            # Esto atrapará los botones sin importar si son <a>, <div> o <li>
            patron_botones = re.compile(r'(Pel[ií]cula|Trailer|Opci[oó]n)', re.IGNORECASE)
            botones = await page.locator("*", has_text=patron_botones).all()
            
            # Filtramos para quedarnos solo con los elementos más pequeños (los botones reales, no todo el contenedor)
            botones_reales = []
            for btn in botones:
                texto = await btn.inner_text()
                if 5 < len(texto.strip()) < 60: # Un botón no tiene un texto gigante
                    botones_reales.append(btn)
            
            # Eliminamos duplicados (a veces el texto está en un <span> dentro de un <a>)
            botones_unicos = []
            textos_vistos = set()
            for btn in botones_reales:
                txt = (await btn.inner_text()).strip()
                if txt not in textos_vistos:
                    textos_vistos.add(txt)
                    botones_unicos.append(btn)

            print(f"Se encontraron {len(botones_unicos)} botones de video.", flush=True)
            
            if not botones_unicos:
                raise Exception("No se encontraron botones con los textos esperados.")

            for i, btn in enumerate(botones_unicos):
                nombre = (await btn.inner_text()).strip().replace("\n", " ")
                print(f"\n[{i+1}/{len(botones_unicos)}] Haciendo clic en: '{nombre}'", flush=True)
                
                try:
                    # Hacemos scroll hacia el botón para asegurar que sea clickeable
                    await btn.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                    
                    # Clic forzado (por si hay algún anuncio transparente encima)
                    await btn.click(force=True, timeout=5000)
                    await page.wait_for_timeout(3000) # Esperar que el iframe cambie
                    
                    # Buscar el iframe del reproductor
                    iframe = page.locator("iframe").first
                    if await iframe.count() > 0:
                        src = await iframe.get_attribute("src")
                        results[nombre] = src
                        print(f"  -> URL del Embed: {src}", flush=True)
                    else:
                        print("  -> No se encontró el iframe.", flush=True)
                        
                except Exception as e:
                    print(f"  -> Error al hacer clic: {e}", flush=True)
                    
                await page.wait_for_timeout(1000)

        except Exception as e:
            print(f"\n❌ ERROR GENERAL: {e}", flush=True)
            print("Guardando captura de pantalla y HTML para depuración...", flush=True)
            try:
                await page.screenshot(path="error.png", full_page=True)
                with open("debug.html", "w", encoding="utf-8") as f:
                    f.write(await page.content())
                print("✅ Se ha guardado 'error.png' y 'debug.html'", flush=True)
            except Exception as debug_error:
                print(f"No se pudo guardar el debug: {debug_error}", flush=True)
        finally:
            await browser.close()
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Proceso terminado. Datos guardados en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
