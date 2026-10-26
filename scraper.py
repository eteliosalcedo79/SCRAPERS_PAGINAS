import asyncio
import json
from playwright.async_api import async_playwright

# --- CONFIGURACIÓN ---
AGENDA_URL = "https://pelotalibre.biz/agenda"
OUTPUT_FILE = "eventos_pelotalibre.json"
MAX_EVENTOS = 10  # Puedes subir este número (ej. 30, 50) si quieres más partidos


async def get_match_iframes(context, url, debug_name=None):
    """Abre la página del partido, hace clic en cada fuente y extrae todos los iframes."""
    nueva = await context.new_page()
    srcs_encontrados = []
    
    try:
        await nueva.goto(url, wait_until="domcontentloaded", timeout=30000)
        # Esperamos a que la página cargue los scripts del reproductor
        await nueva.wait_for_timeout(4000) 
        
        # Buscamos los botones de las fuentes. 
        # Basado en tu imagen, tienen la clase 'btn' o son etiquetas 'button' con el texto FUENTE
        opciones = nueva.locator("button:has-text('FUENTE'), a:has-text('FUENTE'), div.btn:has-text('FUENTE')")
        count = await opciones.count()

        if count == 0:
            # Respaldo: si no encontramos los botones, intentamos extraer el iframe directo
            try:
                await nueva.wait_for_selector("iframe", state="attached", timeout=10000)
                iframe = nueva.locator("iframe").first
                src = await iframe.get_attribute("src") or await iframe.get_attribute("data-src")
                if src:
                    srcs_encontrados.append(src)
            except Exception:
                pass
            return srcs_encontrados

        print(f"     Encontradas {count} fuentes. Extrayendo...", flush=True)

        # Hacemos clic en cada fuente una por una
        for i in range(count):
            btn = opciones.nth(i)
            try:
                # Hacemos clic (force=True por si hay algún anuncio flotante encima)
                await btn.click(force=True)
                # Esperamos un poco más para que el iframe del video se actualice
                await nueva.wait_for_timeout(3500) 
                
                # Buscamos el iframe del reproductor
                iframe = nueva.locator("iframe").first
                src = await iframe.get_attribute("src")
                
                if not src or src.strip() == "":
                    src = await iframe.get_attribute("data-src")
                    
                if src and src not in srcs_encontrados:
                    srcs_encontrados.append(src)
                    
            except Exception as e:
                # Si una fuente falla o da error, saltamos a la siguiente
                pass
                
        return srcs_encontrados

    except Exception as e:
        print(f"       ⚠️ Error en {debug_name}: {e}", flush=True)
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

        print("Abriendo agenda de Pelota Libre...", flush=True)
        try:
            await page.goto(AGENDA_URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error cargando la agenda: {e}", flush=True)
            await browser.close()
            return

        print("Extrayendo partidos del HTML...", flush=True)
        
        # Extraemos los datos directamente de la estructura HTML
        eventos = await page.evaluate("""
            () => {
                const out = [];
                document.querySelectorAll('.source-agenda-event').forEach(ev => {
                    const tituloEl = ev.querySelector('.source-agenda-eventtext strong');
                    const enlaceEl = ev.querySelector('.agenda-open-match');
                    
                    if (tituloEl && enlaceEl) {
                        let titulo = tituloEl.innerText.trim();
                        let href = enlaceEl.getAttribute('href');
                        
                        // Solo agregamos si tiene enlace
                        if (href) {
                            out.push({ titulo: titulo, href: href });
                        }
                    }
                });
                return out;
            }
        """)

        total_eventos = len(eventos)
        print(f"Se encontraron {total_eventos} partidos en total. Procesando los primeros {MAX_EVENTOS}...", flush=True)

        # --- PASO 2: Iterar sobre cada partido ---
        for i, evento in enumerate(eventos[:MAX_EVENTOS]):
            titulo = evento["titulo"]
            href = evento["href"]
            
            # Limpiamos el título para que se vea mejor en el JSON (quitamos el nombre de la liga)
            nombre_limpio = titulo.split(':')[-1].strip() if ':' in titulo else titulo
            
            # Construir URL completa
            if href.startswith("http"):
                url_partido = href
            else:
                url_partido = "https://pelotalibre.biz" + href

            # Evitar claves duplicadas en el JSON
            clave = nombre_limpio
            n = 2
            while clave in results:
                clave = f"{nombre_limpio} ({n})"
                n += 1

            print(f"\n[{i+1}/{min(MAX_EVENTOS, total_eventos)}] Procesando: {clave}", flush=True)

            # Extraemos la lista de iframes del partido
            srcs = await get_match_iframes(context, url_partido, debug_name=f"partido_{i+1}")
            
            results[clave] = srcs
            
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
