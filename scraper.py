import asyncio
import json
from playwright.async_api import async_playwright

BASE_URL = "https://futbol-libre.app/agenda"
OUTPUT_FILE = "resultados.json"
DEBUG = True  # si algo falla, guarda HTML para diagnosticar

# Lista de posibles selectores de eventos (se prueba en orden)
EVENT_SELECTORS = [
    "article",
    ".event",
    ".match",
    "[class*='event-item']",
    "[class*='match-item']",
    "[class*='evento']",
    "li[class*='event']",
]

async def dump(page, name):
    if DEBUG:
        try:
            with open(f"debug_{name}.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
            print(f"      [debug] {name} guardado", flush=True)
        except Exception:
            pass

async def find_event_selector(page):
    """Devuelve el primer selector de eventos que encuentre elementos útiles."""
    for sel in EVENT_SELECTORS:
        try:
            await page.wait_for_selector(sel, timeout=3000)
            n = await page.locator(sel).count()
            if n >= 2:  # al menos 2 eventos para evitar falsos positivos
                print(f"Selector de eventos elegido: '{sel}' ({n} elementos)", flush=True)
                return sel
        except Exception:
            continue
    return None

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
            await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error cargando agenda: {e}", flush=True)
            await browser.close()
            return

        # Cloudflare
        content = await page.content()
        if "Just a moment" in content or "cf-challenge" in content:
            print("⚠️ Bloqueado por Cloudflare.", flush=True)
            await dump(page, "cloudflare")
            await browser.close()
            return

        event_sel = await find_event_selector(page)
        if not event_sel:
            print("❌ No se detectó el selector de eventos.", flush=True)
            await dump(page, "agenda_fail")
            await browser.close()
            return

        total = await page.locator(event_sel).count()
        print(f"Total eventos: {total}", flush=True)

        for i in range(total):
            evento = page.locator(event_sel).nth(i)

            # Título (primera línea de texto no vacía)
            try:
                texto = (await evento.inner_text()).strip()
                titulo = next((l.strip() for l in texto.split("\n") if l.strip()), f"Evento_{i+1}")
            except Exception:
                titulo = f"Evento_{i+1}"

            print(f"\n[{i+1}/{total}] {titulo}", flush=True)
            results.setdefault(titulo, {})

            # 1) Abrir acordeón
            try:
                await evento.scroll_into_view_if_needed()
                await evento.click()
                await page.wait_for_timeout(1200)
            except Exception as e:
                print(f"  ⚠️ No se pudo abrir el acordeón: {e}", flush=True)
                continue

            # 2) Localizar "Abrir partido"
            abrir = None
            for estrategia in [
                lambda: page.locator("text=Abrir partido").first,
                lambda: page.locator("a:has-text('Abrir partido')").first,
                lambda: page.locator("button:has-text('Abrir partido')").first,
                lambda: page.locator("[href*='partido'], [href*='canal']").first,
            ]:
                try:
                    cand = estrategia()
                    if await cand.count() > 0:
                        abrir = cand
                        break
                except Exception:
                    continue

            if abrir is None:
                print("  ⚠️ No se encontró 'Abrir partido'.", flush=True)
                await dump(page, f"acordeon_{i+1}_fail")
                continue

            # 3) Abrir en pestaña nueva
            try:
                async with context.expect_page(timeout=15000) as info:
                    await abrir.click()
                partido = await info.value
                await partido.wait_for_load_state("domcontentloaded", timeout=30000)
                await partido.wait_for_timeout(3000)
            except Exception as e:
                print(f"  ⚠️ No se abrió pestaña nueva: {e}", flush=True)
                continue

            # 4) Esperar iframe
            try:
                await partido.wait_for_selector("iframe", state="attached", timeout=15000)
            except Exception as e:
                print(f"  ⚠️ Sin iframe: {e}", flush=True)
                await dump(partido, f"partido_{i+1}_fail")
                await partido.close()
                await page.reload(wait_until="domcontentloaded")
                await page.wait_for_selector(event_sel, timeout=15000)
                continue

            # 5) Botones de canal: probar varios selectores
            canal_sel = None
            for sel in ["button", "[role='button']", ".canal", "[class*='fuente']",
                        "[class*='canal']", "[class*='channel']", "a[href*='canal']"]:
                try:
                    n = await partido.locator(sel).count()
                    # Filtramos: queremos >=2 botones (Fuente 1, Fuente 2...)
                    if n >= 2:
                        canal_sel = sel
                        print(f"  Selector de canales: '{sel}' ({n} botones)", flush=True)
                        break
                except Exception:
                    continue

            if canal_sel is None:
                print("  ⚠️ No se detectaron botones de canal.", flush=True)
                await dump(partido, f"partido_{i+1}_sin_canales")
                await partido.close()
                await page.reload(wait_until="domcontentloaded")
                await page.wait_for_selector(event_sel, timeout=15000)
                continue

            canales = partido.locator(canal_sel)
            n_canales = await canales.count()

            for k in range(n_canales):
                try:
                    canal = partido.locator(canal_sel).nth(k)
                    nombre = (await canal.inner_text()).strip() or f"Canal_{k+1}"
                    # Filtrar botones que no son canales reales
                    if nombre.lower() in ("abrir partido", "recargar", ""):
                        continue

                    print(f"     - {nombre}", flush=True)
                    await canal.click()
                    await partido.wait_for_timeout(2500)

                    # Releemos el iframe tras el clic
                    iframe = partido.locator("iframe").first
                    src = await iframe.get_attribute("src")
                    results[titulo][nombre] = src
                    print(f"       → {src}", flush=True)
                except Exception as e:
                    print(f"       ⚠️ {e}", flush=True)
                    try:
                        results[titulo][nombre] = None
                    except Exception:
                        pass

            # 6) Cerrar pestaña del partido y volver
            try:
                await partido.close()
            except Exception:
                pass

            try:
                await page.reload(wait_until="domcontentloaded")
                await page.wait_for_selector(event_sel, timeout=15000)
            except Exception:
                await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_selector(event_sel, timeout=15000)

        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Guardado en {OUTPUT_FILE}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
