import asyncio
import json
from playwright.async_api import async_playwright

BASE_URL = "pirlotv.la/home.php"
OUTPUT_FILE = "resultados.json"  

async def main():
    results = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print("Abriendo página principal...", flush=True)
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        
        print("Buscando enlaces de canales...", flush=True)
        try:
            await page.wait_for_selector("a[href*='/canales/']", timeout=15000)
        except Exception as e:
            print(f"No se encontraron canales. Error: {e}", flush=True)
            await browser.close()
            return

        # ✅ EXTRAEMOS TODOS LOS ENLACES DE UNA SOLA VEZ (Evita el timeout)
        canal_links = await page.locator("a[href*='/canales/']").all()
        canales_a_procesar = []
        
        for link in canal_links:
            nombre = (await link.inner_text()).strip()
            href = await link.get_attribute("href")
            if not href.startswith("http"):
                href = BASE_URL.rstrip("/") + href
            canales_a_procesar.append({"nombre": nombre, "href": href})
            
        total_canales = len(canales_a_procesar)
        print(f"Se encontraron {total_canales} canales en total.", flush=True)
        
        # Iteramos sobre la lista que ya tenemos guardada
        for i, canal in enumerate(canales_a_procesar): 
            print(f"\n[{i+1}/{total_canales}] Procesando: {canal['nombre']}", flush=True)
            
            try:
                # Vamos directo a la URL del canal
                await page.goto(canal["href"], wait_until="domcontentloaded", timeout=30000)
                
                # Esperamos a que aparezcan las opciones
                await page.wait_for_selector("text=/OPCIÓN/", timeout=10000)
                
                opciones = await page.locator("text=/OPCIÓN/").all()
                print(f"  -> Encontradas {len(opciones)} opciones.", flush=True)
                
                results[canal['nombre']] = {}
                for j in range(len(opciones)):
                    btn = page.locator("text=/OPCIÓN/").nth(j)
                    nombre_opcion = (await btn.inner_text()).strip()
                    
                    await btn.click(timeout=5000)
                    await page.wait_for_timeout(2000) # Esperar 2 seg que cambie el iframe
                    
                    iframe = page.locator("iframe").first
                    src = await iframe.get_attribute("src")
                    results[canal['nombre']][nombre_opcion] = src
                    print(f"     - {nombre_opcion}: OK", flush=True)
                    
            except Exception as e:
                # Si un canal falla, lo saltamos y seguimos con el siguiente
                print(f"  -> Error procesando {canal['nombre']}: {e}", flush=True)
                continue
            
            # Pequeña pausa de 1 segundo entre canal y canal para no saturar el servidor
            await page.wait_for_timeout(1000)

        await browser.close()
    
    # 💾 Guardamos en resultados.json (esto borra lo anterior y escribe lo nuevo)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Datos guardados en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
