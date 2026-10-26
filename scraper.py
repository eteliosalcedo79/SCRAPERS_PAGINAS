import asyncio
import json
from playwright.async_api import async_playwright

# --- CONFIGURACIÓN ---
SITE_ROOT = "https://deporflix.pe"
OUTPUT_FILE = "canales_deporflix.json"


async def get_iframe_src(context, url, debug_name=None):
    """Abre una pestaña nueva con la URL dada y extrae el src del primer iframe."""
    nueva = await context.new_page()
    try:
        await nueva.goto(url, wait_until="domcontentloaded", timeout=30000)
        # Esperamos a que el reproductor (iframe) esté presente
        await nueva.wait_for_selector("iframe", state="attached", timeout=15000)
        # Espera extra por si el JS del reproductor carga el src con retraso
        await nueva.wait_for_timeout(2500)
        
        iframe = nueva.locator("iframe").first
        src = await iframe.get_attribute("src")
        return src
    except Exception as e:
        print(f"       ⚠️ Error extrayendo iframe: {e}", flush=True)
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
        print("Buscando lista de canales...", flush=True)
        
        # Selector basado en el HTML real que enviaste
        channel_selector = ".items.featured article"
        
        try:
            # Esperamos hasta 30s a que aparezca el primer canal
            await page.wait_for_selector(channel_selector, timeout=30000)
        except Exception as e:
            print(f"No se encontraron canales tras 30s de espera: {e}", flush=True)
            await browser.close()
            return

        # Extraemos los enlaces y los nombres directamente del H3
        canales = await page.evaluate("""
            () => {
                const out = [];
                // Buscamos cada tarjeta de canal
                document.querySelectorAll('.items.featured article').forEach(article => {
                    // El enlace real y el nombre están dentro de la etiqueta h3 > a
                    const enlace = article.querySelector('.data h3 a');
                    if (enlace) {
                        const nombre = enlace.innerText.trim();
                        const href = enlace.getAttribute('href');
                        
                        if (href && nombre) {
                            // Evitar duplicados por URL
                            if (!out.some(item => item.href === href)) {
                                out.push({ nombre: nombre, href: href });
                            }
                        }
                    }
                });
                return out;
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

            # Usamos la función para obtener el iframe del canal
            src = await get_iframe_src(context, url_canal, debug_name=f"canal_{i+1}")
            
            results[nombre_canal] = src
            
            if src:
                print(f"     ✅ Embed: {src}", flush=True)
            else:
                print(f"     ❌ No se encontró embed", flush=True)

        await browser.close()

    # Guardar resultados en JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Guardado en {OUTPUT_FILE}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
