import asyncio
import json
from playwright.async_api import async_playwright

# --- CONFIGURACIÓN ---
# URL del partido (asegúrate de que tenga el https:// correcto)
TARGET_URL = "https://sportiskos.space/latin/soccer.html?p=soccer&d=sportiskos.space&m=620&v=20260917a&ref=futbolvivo.tv"
OUTPUT_FILE = "resultados.json"

async def main():
    results = {}

    async with async_playwright() as p:
        # Lanzamos el navegador en modo headless (sin interfaz gráfica)
        browser = await p.chromium.launch(headless=True)
        
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        print(f"Abriendo página del partido: {TARGET_URL}", flush=True)
        try:
            # Esperamos a que cargue el DOM
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            # Damos un tiempo extra para que los scripts del reproductor inyecten el iframe
            await page.wait_for_timeout(6000) 
        except Exception as e:
            print(f"Error cargando la página: {e}", flush=True)
            await browser.close()
            return

        print("Extrayendo el embed del reproductor...", flush=True)
        
        src_encontrado = None

        try:
            # Buscamos el iframe. La mayoría de reproductores usan el primer iframe visible.
            iframe = page.locator("iframe").first
            await iframe.wait_for(state="attached", timeout=10000)
            
            # Extraemos el src o data-src
            src_encontrado = await iframe.get_attribute("src")
            if not src_encontrado or src_encontrado.strip() == "":
                src_encontrado = await iframe.get_attribute("data-src")

        except Exception as e:
            print(f"⚠️ Error buscando el iframe directamente: {e}", flush=True)
            # Plan B: Si no lo encuentra con el localizador, lo busca en el HTML crudo
            html_content = await page.content()
            # (Opcional) Guardar HTML para depurar si falla
            # with open("debug_page.html", "w", encoding="utf-8") as f: f.write(html_content)

        # Guardamos los resultados
        if src_encontrado:
            print(f"✅ Embed encontrado: {src_encontrado}", flush=True)
            results["embed_partido"] = src_encontrado
        else:
            print("❌ No se pudo encontrar el enlace del embed (iframe).", flush=True)
            results["embed_partido"] = None

        await browser.close()

    # Guardar en el JSON solicitado
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Resultados guardados exitosamente en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
