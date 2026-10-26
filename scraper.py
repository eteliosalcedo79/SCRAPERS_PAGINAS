import asyncio
import json
from playwright.async_api import async_playwright

TARGET_URL = "https://sportiskos.space/latin/soccer.html?p=soccer&d=sportiskos.space&m=620&v=20260917a&ref=futbolvivo.tv"
OUTPUT_FILE = "resultados.json"

async def main():
    results = {}
    urls_capturadas = []

    async with async_playwright() as p:
        # Se recomienda headless=False en local para depurar; en GitHub Actions usa xvfb-run
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        # --- Interceptor de red ---
        # Captura cualquier URL que el navegador intente cargar
        page.on("request", lambda req: urls_capturadas.append(req.url))

        print("1. Abriendo página principal...", flush=True)
        try:
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000)
        except Exception as e:
            print(f"Error: {e}", flush=True)
            await browser.close()
            return

        # Obtener el iframe del envoltorio
        src_intermedio = None
        try:
            iframe = page.locator("iframe").first
            await iframe.wait_for(state="attached", timeout=10000)
            src_intermedio = await iframe.get_attribute("src")
            if not src_intermedio:
                src_intermedio = await iframe.get_attribute("data-src")
        except Exception:
            pass

        if not src_intermedio:
            print("❌ No se encontró el envoltorio inicial.", flush=True)
            await browser.close()
            return

        print(f"2. Envoltorio: {src_intermedio[:60]}...", flush=True)
        print("3. Entrando al envoltorio y capturando red (15s)...", flush=True)

        wrapper_page = await context.new_page()
        # También interceptamos la red dentro del envoltorio
        wrapper_page.on("request", lambda req: urls_capturadas.append(req.url))

        try:
            await wrapper_page.goto(src_intermedio, wait_until="domcontentloaded", timeout=30000)
            # Espera larga para permitir que el reproductor cargue y haga sus peticiones
            await wrapper_page.wait_for_timeout(15000) 
        except Exception as e:
            print(f"Error en envoltorio: {e}", flush=True)

        # --- Filtrar las URLs capturadas ---
        embed_final = None
        m3u8_final = None

        # Patrones que suelen identificar al reproductor real
        patrones_embed = ["embed", "player", "repro", "stream", "canal", "espn", "directv", "fox", "tnt", "bein"]
        
        for url in urls_capturadas:
            # Descartar el propio envoltorio, publicidad y scripts
            if "kora-plus" in url or "frame.php" in url or "google" in url or "ads" in url or ".js" in url or ".css" in url:
                continue
            
            if url.endswith(".m3u8") or ".m3u8?" in url:
                m3u8_final = url
                continue

            if ".php" in url and any(p in url.lower() for p in patrones_embed):
                embed_final = url
                # Si ya encontramos el embed, preferimos ese sobre el m3u8
                break

        # Guardar resultados (priorizando el embed, luego el m3u8)
        if embed_final:
            print(f"\n✅ Embed REAL encontrado: {embed_final}", flush=True)
            results["embed_partido"] = embed_final
        elif m3u8_final:
            print(f"\n✅ No se encontró embed .php, pero sí HLS directo: {m3u8_final}", flush=True)
            results["embed_partido"] = m3u8_final
        else:
            print("\n❌ No se pudo capturar el embed ni el HLS.", flush=True)
            results["embed_partido"] = None
            # Guardar HTML para depurar si falla
            try:
                with open("debug_wrapper.html", "w", encoding="utf-8") as f:
                    f.write(await wrapper_page.content())
                print("   -> Guardado debug_wrapper.html para inspección.", flush=True)
            except:
                pass

        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"✅ Resultados guardados en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
