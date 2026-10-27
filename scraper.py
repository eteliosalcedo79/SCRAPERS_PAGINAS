import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async  # <-- NUEVO

URL = "https://futbollibres.ad/"
SITE_ROOT = "https://futbollibres.ad"
OUTPUT_FILE = "eventos2.json"

PAGE_UTC_OFFSET = 2
OUT_UTC_OFFSET = -5
N_WORKERS = 2
BLOQUEAR_IFRAMES = False 

LISTA_JS = """
() => {
    const results = [];
    const timeRegex = /(\\d{1,2}:\\d{2}(?:am|pm))/i;
    document.querySelectorAll('div, tr, li').forEach(el => {
        if (el.children.length === 0 || !el.innerText.includes(' vs ')) return;
        const text = el.innerText;
        if (text.split('\\n').length > 5) return;
        const timeMatch = text.match(timeRegex);
        if (!timeMatch) return;
        const lines = text.split('\\n').map(s => s.trim()).filter(s => s);
        const matchLine = lines.find(l => l.includes(' vs '));
        if (matchLine) {
            let title = matchLine.replace(timeMatch[0], '').trim();
            title = title.replace(/[\\uD800-\\uDBFF][\\uDC00-\\uDFFF]/g, '').trim();
            title = title.replace(/^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$/g, '').trim();
            results.push({ titulo: title, hora: timeMatch[0] });
        }
    });
    const unique = [];
    const seen = new Set();
    for (const r of results) {
        const key = r.titulo + '|' + r.hora;
        if (!seen.has(key)) { seen.add(key); unique.push(r); }
    }
    return unique;
}
"""

def parse_time_to_24h(time_str):
    time_str = time_str.lower().strip()
    match = re.search(r'(\d{1,2}):(\d{2})(am|pm)', time_str)
    if not match: return time_str
    h = int(match.group(1))
    m = match.group(2)
    ampm = match.group(3)
    if ampm == 'pm' and h != 12: h += 12
    if ampm == 'am' and h == 12: h = 0
    return f"{h:02d}:{m}"

def limpiar_nombre(texto):
    n = texto.replace("▶", " ").replace("\n", " ")
    n = re.sub(r"Calidad \d+p", "", n, flags=re.IGNORECASE)
    n = re.sub(r"\s+", " ", n).strip()
    return n.strip(" |·-").strip()

def calcular_horas(horas):
    tz_page = timezone(timedelta(hours=PAGE_UTC_OFFSET))
    tz_out = timezone(timedelta(hours=OUT_UTC_OFFSET))
    fecha = datetime.now(tz_page).date()
    previo = -1
    salida = []
    for hora in horas:
        try: h, m = map(int, hora.split(":"))
        except Exception:
            salida.append((hora, ""))
            continue
        minutos = h * 60 + m
        if minutos < previo: fecha += timedelta(days=1)
        previo = minutos
        dt = datetime(fecha.year, fecha.month, fecha.day, h, m, tzinfo=tz_page)
        salida.append((dt.astimezone(tz_out).strftime("%H:%M"), dt.astimezone(timezone.utc).isoformat()))
    return salida

def construir_evento(titulo, hora, time_utc, canales):
    if ": " in titulo: liga, partido = titulo.split(": ", 1)
    else: liga, partido = "", titulo
    return {
        "time": hora, "time_utc": time_utc,
        "match": partido.strip(), "league": liga.strip(),
        "flag": "⚽", "channels": canales,
    }

async def cargar_agenda(page):
    await page.goto(URL, wait_until="networkidle", timeout=60000)
    try:
        await page.wait_for_selector('text=/\\s+vs\\s+/i', state="attached", timeout=45000)
    except Exception:
        try:
            await page.wait_for_selector('table', state="attached", timeout=20000)
        except Exception:
            # Si ni siquiera hay tabla, guardamos debug y lanzamos error
            await page.screenshot(path="debug_futbollibres.png", full_page=True)
            with open("debug_futbollibres.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
            print("📸 Debug guardado: debug_futbollibres.png / .html", flush=True)
            raise
    await page.wait_for_timeout(1000)

async def procesar_evento(page, titulo):
    canales_evento = []
    try:
        await cargar_agenda(page)
        evento_li = page.locator('div, tr, li').filter(has_text=titulo).filter(has_text=" vs ").first
        await evento_li.click()
        try: await page.wait_for_selector('text=/Calidad \\d+p/i', timeout=5000)
        except: pass
        canales = page.locator('div, a, li').filter(has_text=re.compile(r'Calidad \d+p', re.I))
        total_canales = await canales.count()
        print(f"  -> {titulo}: {total_canales} canales", flush=True)
        for j in range(total_canales):
            try:
                canal_elem = canales.nth(j)
                texto_canal = await canal_elem.inner_text()
                nombre_canal = limpiar_nombre(texto_canal)
                if len(nombre_canal) < 2 or "vs" in nombre_canal: continue
                async with page.context.expect_page(timeout=15000) as new_page_info:
                    await canal_elem.click()
                new_page = await new_page_info.value
                await new_page.wait_for_load_state('domcontentloaded')
                try:
                    await new_page.wait_for_selector('iframe', timeout=8000)
                    src = await new_page.evaluate("() => { const f = document.querySelector('iframe'); return f ? f.src : ''; }")
                    if src:
                        if src.startswith("/"): src = SITE_ROOT + src
                        canales_evento.append({"name": nombre_canal, "url": src})
                        print(f"     ✅ {nombre_canal}: {src}", flush=True)
                    else: print(f"     ❌ {nombre_canal}: sin src", flush=True)
                except Exception as e: print(f"     ❌ {nombre_canal}: iframe no encontrado ({e})", flush=True)
                await new_page.close()
            except Exception as e: print(f"     ⚠️ Error al abrir canal: {e}", flush=True)
    except Exception as e: print(f"  ⚠️ Error con el evento {titulo}: {e}", flush=True)
    return canales_evento

async def worker(context, cola, resultados, wid):
    page = await context.new_page()
    await stealth_async(page)  # <-- Aplicamos stealth a cada página
    page.set_default_timeout(30000) 
    while True:
        try: i, titulo = cola.get_nowait()
        except asyncio.QueueEmpty: break
        try: resultados[i] = await procesar_evento(page, titulo)
        except Exception as e:
            print(f"  ⚠️ Error grave con {titulo}: {e}", flush=True)
            resultados[i] = []
    await page.close()

async def filtrar(route):
    try:
        req = route.request
        if req.resource_type in ("image", "media", "font"):
            await route.abort(); return
    except Exception: pass
    await route.continue_()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            viewport={"width": 390, "height": 844},
        )
        await context.route("**/*", filtrar)
        page = await context.new_page()
        await stealth_async(page)  # <-- Aplicamos stealth a la página principal
        page.set_default_timeout(30000)
        print("🌐 Abriendo futbollibres.ad...", flush=True)
        try:
            await cargar_agenda(page)
            await page.wait_for_timeout(1500)
        except Exception as e:
            print(f"Error cargando página: {e}", flush=True)
            await browser.close(); return
        datos = await page.evaluate(LISTA_JS)
        await page.close()
        print(f"Se encontraron {len(datos)} eventos.", flush=True)
        if not datos:
            print("⚠️ No se encontraron eventos. Revisa el HTML de debug.", flush=True)
            await browser.close(); return
        horas_24h = [parse_time_to_24h(d["hora"]) for d in datos]
        horas = calcular_horas(horas_24h)
        cola = asyncio.Queue()
        for i, d in enumerate(datos): cola.put_nowait((i, d["titulo"]))
        resultados = {}
        n = max(1, min(N_WORKERS, len(datos)))
        await asyncio.gather(*(worker(context, cola, resultados, w + 1) for w in range(n)))
        await browser.close()
    events = []
    for i, d in enumerate(datos):
        hora, time_utc = horas[i]
        events.append(construir_evento(d["titulo"], hora, time_utc, resultados.get(i, [])))
    ahora = datetime.now(timezone.utc)
    salida = {
        "actualizado_en": ahora.isoformat(),
        "fecha": ahora.astimezone(timezone(timedelta(hours=OUT_UTC_OFFSET))).strftime("%Y-%m-%d"),
        "fuente": "futbollibres.ad-playwright",
        "contar": len(events),
        "contar_con_canales": sum(1 for e in events if e["channels"]),
        "events": events, "eventos": events,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Guardado en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
