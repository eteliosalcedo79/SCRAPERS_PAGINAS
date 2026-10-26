import asyncio
import json
from playwright.async_api import async_playwright

# --- CONFIGURACIÓN ---
TARGET_URL = "https://sportiskos.space/latin/soccer.html?p=soccer&d=sportiskos.space&m=620&v=20260917a&ref=futbolvivo.tv"
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

        print(f"1. Abriendo página principal...", flush=True)
        try:
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000) 
        except Exception as e:
            print(f"Error cargando la página: {e}", flush=True)
            await browser.close()
            return

        src_final = None

        try:
            # 1. Extraemos el primer iframe (el de kora-plus)
            iframe = page.locator("iframe").first
            await iframe.wait_for(state="attached", timeout=10000)
            
            src_intermedio = await iframe.get_attribute("src")
            if not src_intermedio:
                src_intermedio = await iframe.get_attribute("data-src")

            if src_intermedio:
                print(f"2. Envoltorio detectado. Entrando en él...", flush=True)
                
                # 2. Entramos al envoltorio (kora-plus)
                wrapper_page = await context.new_page()
                await wrapper_page.goto(src_intermedio, wait_until="domcontentloaded", timeout=30000)
                await wrapper_page.wait_for_timeout(5000) # Esperamos a que cargue el video
                
                # 3. Buscamos el iframe real del video dentro del envoltorio
                # Buscaremos todos los iframes y filtraremos el que parece un reproductor
                iframes_internos = wrapper_page.locator("iframe")
                count = await iframes_internos.count()
                
                print(f"   Se encontraron {count} iframes dentro del envoltorio. Analizando...", flush=True)
                
                for i in range(count):
                    inner_iframe = iframes_internos.nth(i)
                    src = await inner_iframe.get_attribute("src")
                    
                    if not src:
                        src = await inner_iframe.get_attribute("data-src")
                        
                    if src:
                        # Filtramos para quedarnos con el enlace del reproductor real
                        # Ignoramos anuncios o el propio envoltorio
                        if "kora-plus" not in src and "google" not in src and "ads" not in src:
                            src_final = src
                            break # Si encontramos el bueno, dejamos de buscar
                
                await wrapper_page.close()
            else:
                # Si no hay envoltorio, es que ya era el enlace final
                src_final = src_intermedio

        except Exception as e:
            print(f"⚠️ Error en el proceso: {e}", flush=True)

        # Guardamos los resultados
        if src_final:
            print(f"\n✅ Embed LIMPIO encontrado: {src_final}", flush=True)
            results["embed_partido"] = src_final
        else:
            print("\n❌ No se pudo encontrar el enlace del embed final.", flush=True)
            results["embed_partido"] = None

        await browser.close()

    # Guardar en el JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"✅ Resultados guardados en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
