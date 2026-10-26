import asyncio
import json
from playwright.async_api import async_playwright

TARGET_URL = "https://sportiskos.space/latin/soccer.html?p=soccer&d=sportiskos.space&m=620&v=20260917a&ref=futbolvivo.tv"
OUTPUT_FILE = "resultados.json"

async def main():
    results = {}
    media_urls = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 900},
        )

        # --- Interceptor de respuestas (aquí está la clave) ---
        async def handle_response(response):
            url = response.url
            content_type = response.headers.get("content-type", "").lower()

            # Detectar manifiestos HLS (.m3u8) o fragmentos de video (.ts/.mp4)
            if any(ext in url.lower() for ext in [".m3u8", ".ts", ".mp4", ".mpd"]):
                if url not in media_urls:
                    media_urls.append(url)
                    print(f"   🎯 Capturado: {url[:100]}...", flush=True)

        page = await context.new_page()
        page.on("response", handle_response)  # Escuchar TODAS las respuestas

        print("1. Abriendo página principal...", flush=True)
        try:
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"Error: {e}", flush=True)
            await browser.close()
            return

        print("2. Buscando el envoltorio...", flush=True)
        src_intermedio = None
        try:
            iframe = page.locator("iframe").first
            await iframe.wait_for(state="attached", timeout=10000)
            src_intermedio = await iframe.get_attribute("src") or await iframe.get_attribute("data-src")
        except Exception:
            pass

        if not src_intermedio:
            print("❌ No se encontró el envoltorio inicial.", flush=True)
            await browser.close()
            return

        print(f"3. Entrando al envoltorio y esperando el video (30s)...", flush=True)
        wrapper_page = await context.new_page()
        wrapper_page.on("response", handle_response)  # Escuchar respuestas DENTRO del envoltorio

        try:
            await wrapper_page.goto(src_intermedio, wait_until="domcontentloaded", timeout=30000)
            # Esperar tiempo suficiente para que el JS del reproductor haga las peticiones
            await wrapper_page.wait_for_timeout(30000)
        except Exception as e:
            print(f"Error en envoltorio: {e}", flush=True)

        # --- Resultados ---
        embed_final = None
        m3u8_final = None

        for url in media_urls:
            if ".m3u8" in url.lower() or ".mpd" in url.lower():
                m3u8_final = url
                break
            elif ".php" in url and "kora-plus" not in url:
                embed_final = url

        if embed_final:
            print(f"\n✅ Embed encontrado: {embed_final}", flush=True)
            results["embed_partido"] = embed_final
        elif m3u8_final:
            print(f"\n✅ HLS directo encontrado: {m3u8_final}", flush=True)
            results["embed_partido"] = m3u8_final
        else:
            print("\n❌ No se pudo capturar el video. Guardando HTML de depuración...", flush=True)
            results["embed_partido"] = None
            try:
                with open("debug_wrapper.html", "w", encoding="utf-8") as f:
                    f.write(await wrapper_page.content())
                print("   -> Guardado debug_wrapper.html", flush=True)
            except:
                pass

        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"✅ Resultados guardados en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
