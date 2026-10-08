import asyncio
import json
from playwright.async_api import async_playwright

CANAL_URL   = "https://deporflix.pe/canales/tnt/"
OUTPUT_FILE = "resultados.json"

# Selector que apunta a los botones reales de opción, no a sus contenedores.
# Ajustá si en el DOM se ven como <li>, <div role="button">, etc.
OPCION_SELECTOR = "text=/^OPCIÓN\\s+\\d+/i"

async def main():
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36")
        )
        page = await context.new_page()

        print("Abriendo canal...", flush=True)
        await page.goto(CANAL_URL, wait_until="domcontentloaded", timeout=30000)

        nombre_canal = "space"
        results[nombre_canal] = {}

        try:
            # Esperamos que aparezcan las opciones (o al menos un iframe)
            try:
                await page.wait_for_selector(OPCION_SELECTOR, timeout=20000)
            except Exception:
                # Si no hay lista de opciones, al menos intentamos el iframe directo
                await page.wait_for_selector("iframe", timeout=15000)
                src = await page.locator("iframe").first.get_attribute("src")
                results[nombre_canal]["OPCIÓN ÚNICA"] = src
                print(f"  -> Sin lista de opciones, iframe directo: {src}", flush=True)

            opciones = await page.locator(OPCION_SELECTOR).all()
            print(f"  -> Encontradas {len(opciones)} opciones.", flush=True)

            ultimo_src = None

            for j, btn in enumerate(opciones):
                nombre_opcion = (await btn.inner_text()).strip()

                try:
                    # Clic sobre la opción
                    await btn.click(timeout=5000)

                    # Esperamos un poco a que cargue el nuevo iframe
                    await page.wait_for_timeout(2500)

                    iframe = page.locator("iframe").first
                    src = await iframe.get_attribute("src")

                    # Guardamos bajo el nombre completo de la opción
                    results[nombre_canal][nombre_opcion] = src

                    if src == ultimo_src:
                        print(f"     - {nombre_opcion}: (mismo src que la anterior)", flush=True)
                    else:
                        print(f"     - {nombre_opcion}: OK", flush=True)

                    ultimo_src = src

                except Exception as e:
                    print(f"     - {nombre_opcion}: ERROR ({e})", flush=True)
                    results[nombre_canal][nombre_opcion] = None

        except Exception as e:
            print(f"  -> Error procesando {nombre_canal}: {e}", flush=True)
            results[nombre_canal]["error"] = str(e)

        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Datos guardados en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
