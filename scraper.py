import asyncio
from playwright.async_api import async_playwright

URL = "https://pirlotvapp.pro/"

async def main():
    async with async_playwright() as p:
        # headless=False para que puedas ver la magia en acción
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        print("🌐 Abriendo la página...", flush=True)
        try:
            await page.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error al cargar: {e}")
            await browser.close()
            return

        # 1. Guardamos el HTML inicial (Aquí deberían estar los eventos)
        await page.wait_for_timeout(3000)
        html_inicial = await page.content()
        with open("1_principal.html", "w", encoding="utf-8") as f:
            f.write(html_inicial)
        print("✅ Guardado: 1_principal.html")

        # 2. Intentamos abrir el primer acordeón (Evento)
        print("🖱️ Intentando clic en el primer evento...", flush=True)
        try:
            # Buscamos un elemento clickeable. Como no sabemos la clase exacta, 
            # buscamos el texto del primer partido que se ve en tu captura.
            # Si falla, intentará con selectores genéricos de tarjetas.
            primer_evento = page.locator("text=AFC Champions League Elite").first
            if await primer_evento.count() == 0:
                # Si no está el texto exacto, intentamos buscar cualquier cosa que parezca un título de partido
                primer_evento = page.locator("div[class*='card'], div[class*='event'], div[class*='match']").first
            
            await primer_evento.click(timeout=5000)
            await page.wait_for_timeout(2000) # Esperamos a que se abra el acordeón
            
            html_acordeon = await page.content()
            with open("2_acordeon.html", "w", encoding="utf-8") as f:
                f.write(html_acordeon)
            print("✅ Guardado: 2_acordeon.html (Con el evento desplegado)")
            
        except Exception as e:
            print(f"⚠️ No se pudo hacer clic en el evento: {e}")
            print("   (No te preocupes, el HTML inicial ya está guardado).")

        # 3. Intentamos abrir el primer canal (Modal)
        print("🖱️ Intentando clic en el primer canal (ESPN)...", flush=True)
        try:
            # Buscamos el botón del canal. Viendo tu captura, tienen un ícono de "play" rojo.
            # Intentamos buscar texto como "ESPN" o "Español"
            primer_canal = page.locator("text=ESPN").first
            if await primer_canal.count() == 0:
                # Si no, buscamos botones genéricos dentro del acordeón
                primer_canal = page.locator("button, a[class*='channel'], li[class*='channel']").first

            await primer_canal.click(timeout=5000)
            await page.wait_for_timeout(3000) # Damos tiempo a que cargue el iframe
            
            html_modal = await page.content()
            with open("3_modal.html", "w", encoding="utf-8") as f:
                f.write(html_modal)
            print("✅ Guardado: 3_modal.html (Con el reproductor abierto)")
            
        except Exception as e:
            print(f"⚠️ No se pudo hacer clic en el canal: {e}")

        print("\n🎉 Proceso terminado. Revisa los archivos HTML en tu carpeta.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
