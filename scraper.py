import asyncio
import json
from playwright.async_api import async_playwright

# --- CONFIGURACIÓN ---
SITE_ROOT = "https://deporflix.pe"
OUTPUT_FILE = "canales_deporflix.json"


async def get_all_iframes(context, url, debug_name=None):
    """Abre la página del canal, hace clic en cada opción y extrae todos los iframes."""
    nueva = await context.new_page()
    srcs_encontrados = []
    
    try:
        await nueva.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # Esperamos un poco a que cargue el reproductor y las opciones
        await nueva.wait_for_timeout(3000)
        
        # Buscamos los botones de opciones. 
        # En la mayoría de estos sitios, son elementos <li> o <a> que contienen la palabra OPCIÓN
        opciones = nueva.locator("li:has-text('OPCIÓN'), a:has-text('OPCIÓN'), .options ul li")
        count = await opciones.count()

        if count == 0:
            # Si no hay botones de opciones, intentamos sacar el iframe por defecto
            try:
                await nueva.wait_for_selector("iframe", state="attached", timeout=10000)
                iframe = nueva.locator("iframe").first
                src = await iframe.get_attribute("src") or await iframe.get_attribute("data-src")
                if src:
                    srcs_encontrados.append(src)
            except Exception:
                pass
            return srcs_encontrados

        print(f"     Encontradas {count} opciones. Extrayendo...", flush=True)

        # Hacemos clic en cada opción
        for i in range(count):
            btn = opciones.nth(i)
            try:
                # Hacemos clic en la opción
                await btn.click()
                # Esperamos a que el iframe se actualice
                await nueva.wait_for_timeout(2500)
                
                # Extraemos el src del iframe actual
                iframe = nueva.locator("iframe").first
                src = await iframe.get_attribute("src")
                
                # A veces los reproductores usan 'data-src' en lugar de 'src'
                if not src or src.strip() == "":
                    src = await iframe.get_attribute("data-src")
                    
                if src and src not in srcs_encontrados:
                    srcs_encontrados.append(src)
                    
            except Exception as e:
                # Si una opción falla, que siga con la siguiente
                pass
                
        return srcs_encontrados

    except Exception as e:
        print(f"       ⚠️ Error general en {debug_name}: {e}", flush=True)
        if debug_name:
            try:
                with open(f"debug_{debug_name}.html", "w", encoding="utf-8") as f:
                    f.write(await nueva.content())
            except Exception:
                pass
        return srcs_encontrados
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
        channel_selector = ".items.featured article"
        
        try:
            await page.wait_for_selector(channel_selector, timeout=30000)
        except Exception as e:
            print(f"No se encontraron canales tras 30s de espera: {e}", flush=True)
            await browser.close()
            return

        canales = await page.evaluate("""
            () => {
                const out = [];
                document.querySelectorAll('.items.featured article').forEach(article => {
                    const enlace = article.querySelector('.data h3 a');
                    if (enlace) {
                        const nombre = enlace.innerText.trim();
                        const href = enlace.getAttribute('href');
                        if (href && nombre) {
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

        # --- PASO 2: Iterar sobre cada canal ---
        for i, canal in enumerate(canales):
            nombre_canal = canal["nombre"]
            href = canal["href"]
            
            if href.startswith("http"):
                url_canal = href
            else:
                url_canal = SITE_ROOT.rstrip("/") + "/" + href.lstrip("/")

            print(f"\n[{i+1}/{total_canales}] Procesando: {nombre_canal}", flush=True)

            # Extraemos la lista de iframes
            srcs = await get_all_iframes(context, url_canal, debug_name=f"canal_{i+1}")
            
            # Guardamos la lista en el JSON
            results[nombre_canal] = srcs
            
            if srcs:
                print(f"     ✅ {len(srcs)} embeds encontrados.", flush=True)
            else:
                print(f"     ❌ No se encontraron embeds.", flush=True)

        await browser.close()

    # Guardar resultados
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Guardado en {OUTPUT_FILE}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
