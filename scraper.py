import asyncio
import json
from playwright.async_api import async_playwright

BASE_URL = "https://pelisjuanita.com/tv/fox-sports"
OUTPUT_FILE = "resultados_pelisjuanita.json"

# ⚠️ Ajusta estos selectores según la estructura real de la página
CHANNEL_CARD_SEL = "div.channel-card"      # Contenedor de cada canal (ej. "FOX SPORTS")
SERVER_TAB_SEL   = "button.server-tab"    # Botones de "Servidor 1", "Servidor 2"...
IFRAME_SEL       = "div.player iframe"     # Iframe del reproductor

async def main():
    resultados = {}

    async with async_playwright() as p:
        # headless=False para evadir protecciones anti-bot si es necesario
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        print(f"Abriendo {BASE_URL} ...", flush=True)
        await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)  # Espera extra para JS

        # 1️⃣ Extraer la lista de canales (si hay varios en la página)
        # Si la página solo muestra un canal a la vez, omite este paso y usa un nombre fijo.
        canales = await page.query_selector_all(CHANNEL_CARD_SEL)
        if not canales:
            print("⚠️ No se encontraron canales con el selector dado. Usando la página actual como único canal.", flush=True)
            canales = [None]  # Tratar la página actual como un solo canal

        for idx, canal_el in enumerate(canales):
            if canal_el:
                # Si hay varios canales, haz clic en cada uno para cargar su reproductor
                nombre_canal = (await canal_el.inner_text()).strip() or f"Canal_{idx+1}"
                await canal_el.click()
                await page.wait_for_timeout(2000)
            else:
                nombre_canal = "FOX SPORTS"  # Nombre fijo si solo hay un canal

            print(f"\n📺 Canal: {nombre_canal}", flush=True)
            resultados[nombre_canal] = {}

            # 2️⃣ Esperar a que aparezcan las pestañas de servidor
            try:
                await page.wait_for_selector(SERVER_TAB_SEL, timeout=10000)
            except:
                print("   ⚠️ No se encontraron pestañas de servidor.", flush=True)
                continue

            servidores = await page.query_selector_all(SERVER_TAB_SEL)
            print(f"   🔗 {len(servidores)} servidores encontrados.", flush=True)

            # 3️⃣ Iterar sobre cada servidor
            for j, servidor_el in enumerate(servidores):
                nombre_servidor = (await servidor_el.inner_text()).strip() or f"Servidor_{j+1}"
                print(f"      -> {nombre_servidor}", flush=True)

                try:
                    await servidor_el.click()
                    # Esperar a que el iframe se cargue o cambie su src
                    await page.wait_for_selector(IFRAME_SEL, state="attached", timeout=8000)
                    await page.wait_for_timeout(1500)  # Margen para que el JS actualice el src

                    iframe_el = await page.query_selector(IFRAME_SEL)
                    src = await iframe_el.get_attribute("src") if iframe_el else None

                    if src:
                        resultados[nombre_canal][nombre_servidor] = src
                        print(f"         ✅ {src}", flush=True)
                    else:
                        print("         ❌ sin src", flush=True)
                        resultados[nombre_canal][nombre_servidor] = None
                except Exception as e:
                    print(f"         ⚠️ Error: {e}", flush=True)
                    resultados[nombre_canal][nombre_servidor] = None

        await browser.close()

    # Guardar JSON con el mismo formato que el scraper original
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Guardado en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
