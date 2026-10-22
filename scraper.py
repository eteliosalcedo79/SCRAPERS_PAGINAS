import asyncio
import json
from playwright.async_api import async_playwright

# URL directa de la película
PELICULA_URL = "https://ganovideo.com/peliculas/hope-el-primer-impacto/"
OUTPUT_FILE = "resultados.json"

async def main():
    results = {}
    
    async with async_playwright() as p:
        # Si la página bloquea el headless, cambia a headless=False para probar
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print(f"Abriendo página de la película: {PELICULA_URL}", flush=True)
        try:
            # Esperamos a que la página cargue
            await page.goto(PELICULA_URL, wait_until="domcontentloaded", timeout=45000)
            
            # Esperamos a que aparezca al menos un botón de fuente de video
            # Usamos un selector de texto que cubra "Trailer", "Pelicula" o "Opción"
            await page.wait_for_selector("text=/Trailer|Pelicula|Opción/i", timeout=20000)
            
            # Localizamos todos los botones de opciones
            botones = await page.locator("text=/Trailer|Pelicula|Opción/i").all()
            print(f"Se encontraron {len(botones)} opciones de video.", flush=True)
            
            for i, btn in enumerate(botones):
                try:
                    # Obtenemos el texto del botón para usarlo como clave
                    nombre_opcion = (await btn.inner_text()).strip()
                    print(f"\n[{i+1}/{len(botones)}] Procesando: {nombre_opcion}", flush=True)
                    
                    # Hacemos clic en el botón
                    await btn.click(timeout=5000)
                    
                    # Esperamos un momento a que el iframe se actualice
                    # Ajusta este tiempo si tu conexión es lenta
                    await page.wait_for_timeout(2500)
                    
                    # Localizamos el primer iframe (el del reproductor principal)
                    iframe = page.locator("iframe").first
                    
                    # Esperamos a que el iframe tenga un atributo src
                    await iframe.wait_for(state="attached", timeout=5000)
                    src = await iframe.get_attribute("src")
                    
                    if src:
                        results[nombre_opcion] = src
                        print(f"     - URL extraída: {src}", flush=True)
                    else:
                        print(f"     - No se encontró 'src' en el iframe.", flush=True)
                        
                except Exception as e:
                    print(f"  -> Error procesando '{nombre_opcion}': {e}", flush=True)
                    continue
                
                # Pequeña pausa entre clics para no saturar
                await page.wait_for_timeout(1000)
                
        except Exception as e:
            print(f"Error general en la página: {e}", flush=True)
        finally:
            await browser.close()
    
    # Guardamos los resultados
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Datos guardados en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
