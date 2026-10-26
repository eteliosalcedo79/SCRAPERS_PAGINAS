import asyncio
import json
from playwright.async_api import async_playwright

# --- CONFIGURACIÓN ---
SITE_ROOT = "https://deporflix.pe"
OUTPUT_FILE = "canales_deporflix.json"

# Selector de la sección de canales en la página principal
CANALES_SECTION_SEL = "h2:has-text('Canales En vivo')" 
# Selector para los enlaces de las tarjetas de canal
CANAL_CARD_SEL = "a[href*='/canal/']" # Ajustar si es necesario


async def get_iframe_src(context, url, debug_name=None):
    """Abre una pestaña nueva con la URL dada y extrae el src del primer iframe."""
    nueva = await context.new_page()
    try:
        await nueva.goto(url, wait_until="domcontentloaded", timeout=30000)
        # Esperamos a que el iframe esté presente (puede tardar por el JS)
        await nueva.wait_for_selector("iframe", state="attached", timeout=15000)
        await nueva.wait_for_timeout(2500) # Espera extra para JS
        
        iframe = nueva.locator("iframe").first
        src = await iframe.get_attribute("src")
        return src
    except Exception as e:
        print(f"       ⚠️ {e}", flush=True)
        if debug_name:
            try:
                with open(f"debug_{debug_name}.html", "w", encoding="utf-8") as f:
                    f.write(await nueva.content())
            except Exception:
                pass
        return None
    finally:
        await nueva.close()


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

        print("Abriendo página principal de Deporflix...", flush=True)
        try:
            await page.goto(SITE_ROOT, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error cargando la página: {e}", flush=True)
            await browser.close()
            return

        # --- PASO 1: Extraer los enlaces de los canales ---
        print("Buscando sección 'Canales En vivo'...", flush=True)
        
        # Esperamos a que la sección esté presente
        try:
            await page.wait_for_selector(CANALES_SECTION_SEL, timeout=20000)
        except Exception as e:
            print(f"No se encontró la sección de canales: {e}", flush=True)
            await browser.close()
            return

        # Extraemos los enlaces de los canales
        canales = await page.evaluate("""
            () => {
                const out = [];
                // Buscamos todos los enlaces que apunten a un canal
                // Ajusta el selector si la estructura es diferente
                document.querySelectorAll('a[href*="/canal/"]').forEach(a => {
                    const nombre = a.innerText.trim().replace(/\\s+/g, ' ');
                    const href = a.getAttribute('href');
                    if (href && nombre) {
                        out.push({nombre, href});
                    }
                });
                // Eliminar duplicados por href
                const unicos = Array.from(new Map(out.map(item => [item.href, item])).values());
                return unicos;
            }
        """)

        total_canales = len(canales)
        print(f"Se encontraron {total_canales} canales.", flush=True)

        # --- PASO 2: Iterar sobre cada canal y extraer el iframe ---
        for i, canal in enumerate(canales):
            nombre_canal = canal["nombre"]
            href = canal["href"]
            
            # Construir URL completa
            if href.startswith("http"):
                url_canal = href
            else:
                url_canal = SITE_ROOT.rstrip("/") + "/" + href.lstrip("/")

            print(f"\n[{i+1}/{total_canales}] Procesando: {nombre_canal}", flush=True)
            print(f"  -> URL: {url_canal}", flush=True)

            # Usamos la función existente para obtener el iframe
            src = await get_iframe_src(context, url_canal, debug_name=f"canal_{i+1}")
            
            results[nombre_canal] = src
            
            if src:
                print(f"     ✅ Embed: {src}", flush=True)
            else:
                print(f"     ❌ No se encontró embed", flush=True)

        await browser.close()

    # Guardar resultados
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Guardado en {OUTPUT_FILE}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
