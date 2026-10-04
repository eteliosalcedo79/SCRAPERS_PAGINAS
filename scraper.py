import asyncio
import json
from playwright.async_api import async_playwright

AGENDA_URL = "https://futbol-libre.app/agenda"
SITE_ROOT  = "https://futbol-libre.app"
OUTPUT_FILE = "resultados.json"

EVENT_SELECTOR   = "div.source-agenda-event"
TITLE_SELECTOR   = ".source-agenda-eventtext strong"
SOURCE_LINK_SEL  = "a.agenda-source-button"


async def get_iframe_src(context, url, debug_name=None):
    """Abre una pestaña nueva con la URL dada y extrae el src del primer iframe."""
    nueva = await context.new_page()
    try:
        await nueva.goto(url, wait_until="domcontentloaded", timeout=30000)
        await nueva.wait_for_selector("iframe", state="attached", timeout=15000)
        # Esperamos un poco por si el JS cambia el iframe tras leer el #source=
        await nueva.wait_for_timeout(2500)
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

        print("Abriendo agenda...", flush=True)
        try:
            await page.goto(AGENDA_URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error cargando agenda: {e}", flush=True)
            await browser.close()
            return

        content = await page.content()
        if "Just a moment" in content or "cf-challenge" in content:
            print("⚠️ Bloqueado por Cloudflare.", flush=True)
            await browser.close()
            return

        try:
            await page.wait_for_selector(EVENT_SELECTOR, timeout=20000)
        except Exception as e:
            print(f"No se encontraron eventos: {e}", flush=True)
            await browser.close()
            return

        # Extraemos TODA la info de la agenda de una sola pasada (rápido y sin stale elements)
        eventos = await page.evaluate("""
            () => {
                const out = [];
                document.querySelectorAll('div.source-agenda-event').forEach(ev => {
                    const tituloEl = ev.querySelector('.source-agenda-eventtext strong');
                    const titulo = tituloEl ? tituloEl.textContent.trim() : '';
                    const fuentes = [];
                    ev.querySelectorAll('a.agenda-source-button').forEach(a => {
                        const nombre = a.querySelector('span')?.textContent.trim() || '';
                        const proveedor = a.querySelector('small')?.textContent.trim() || '';
                        fuentes.push({
                            nombre: nombre + (proveedor ? ' · ' + proveedor : ''),
                            href: a.getAttribute('href')
                        });
                    });
                    out.push({titulo, fuentes});
                });
                return out;
            }
        """)

        total_eventos = len(eventos)
        print(f"Se encontraron {total_eventos} eventos.", flush=True)

        for i, ev in enumerate(eventos):
            titulo = ev["titulo"] or f"Evento_{i+1}"
            fuentes = ev["fuentes"]

            print(f"\n[{i+1}/{total_eventos}] {titulo}  ({len(fuentes)} fuentes)", flush=True)

            # Evitar claves duplicadas en el JSON
            clave = titulo
            n = 2
            while clave in results:
                clave = f"{titulo} ({n})"
                n += 1

            results[clave] = {}

            for j, f in enumerate(fuentes):
                nombre = f["nombre"] or f"Fuente_{j+1}"
                href = f["href"]
                if not href:
                    continue
                if href.startswith("http"):
                    url = href
                else:
                    url = SITE_ROOT.rstrip("/") + "/" + href.lstrip("/")

                print(f"  -> {nombre}: {url}", flush=True)
                src = await get_iframe_src(context, url, debug_name=f"partido_{i+1}_{j+1}")
                results[clave][nombre] = src
                if src:
                    print(f"     ✅ {src}", flush=True)
                else:
                    print(f"     ❌ sin src", flush=True)

        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Guardado en {OUTPUT_FILE}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
