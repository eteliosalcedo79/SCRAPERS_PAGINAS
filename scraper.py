import asyncio
import json
from playwright.async_api import async_playwright

BASE_URL = "https://deporflix.pe/"
OUTPUT_FILE = "canales_iframes.json"

async def main():
    results = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Configuramos un User-Agent realista para que el sitio no bloquee al robot
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print("Abriendo página principal...", flush=True)
        # Esperamos máximo 30 segundos a que cargue la página
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        
        print("Buscando enlaces de canales...", flush=True)
        try:
            # Esperamos máximo 15 segundos a que aparezca al menos un canal
            await page.wait_for_selector("a[href*='/canales/']", timeout=15000)
        except Exception as e:
            print(f"No se encontraron canales. La página tardó demasiado o bloqueó el acceso. Error: {e}", flush=True)
            await browser.close()
            return

        canal_links = await page.locator("a[href*='/canales/']").all()
        total_canales = len(canal_links)
        print(f"Se encontraron {total_canales} canales en total.", flush=True)
        
        # ⚠️ LIMITAMOS A LOS PRIMEROS 3 CANALES PARA LA PRUEBA
        # (Luego puedes quitar el [:3] para hacerlo con todos)
        for i in range(min(total_canales, 3)): 
            link = page.locator("a[href*='/canales/']").nth(i)
            nombre_canal = (await link.inner_text()).strip()
            href = await link.get_attribute("href")
            if not href.startswith("http"):
                href = BASE_URL.rstrip("/") + href
                
            print(f"\n[{i+1}] Procesando: {nombre_canal}", flush=True)
            
            # Vamos directo a la URL del canal
            await page.goto(href, wait_until="domcontentloaded", timeout=30000)
            
            try:
                # Esperamos máximo 10 segundos a que aparezca la palabra OPCIÓN
                await page.wait_for_selector("text=/OPCIÓN/", timeout=10000)
            except:
                print(f"  -> No se encontraron opciones para {nombre_canal}.", flush=True)
                continue
            
            opciones = await page.locator("text=/OPCIÓN/").all()
            print(f"  -> Encontradas {len(opciones)} opciones.", flush=True)
            
            results[nombre_canal] = {}
            for j in range(len(opciones)):
                btn = page.locator("text=/OPCIÓN/").nth(j)
                nombre_opcion = (await btn.inner_text()).strip()
                
                try:
                    await btn.click(timeout=5000)
                    await page.wait_for_timeout(2000) # Esperar 2 seg que cambie el iframe
                    
                    iframe = page.locator("iframe").first
                    src = await iframe.get_attribute("src")
                    results[nombre_canal][nombre_opcion] = src
                    print(f"     - {nombre_opcion}: OK", flush=True)
                except Exception as e:
                    print(f"     - {nombre_opcion}: FALLÓ ({e})", flush=True)

        await browser.close()
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Datos guardados en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
