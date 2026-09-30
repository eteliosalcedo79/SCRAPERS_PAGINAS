import asyncio
import json
from playwright.async_api import async_playwright

# URL real de la página principal
BASE_URL = "https://deporflix.pe/"
OUTPUT_FILE = "canales_iframes.json"

async def main():
    results = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"Abriendo página principal: {BASE_URL}")
        await page.goto(BASE_URL, wait_until="networkidle")
        
        # 1. EXTRAER ENLACES DE CANALES
        # Esperamos a que los enlaces de "Ver canal" se carguen (pueden tardar un poco)
        print("Esperando a que carguen los canales...")
        await page.wait_for_selector("a[href*='/canales/']", timeout=30000)
        
        # Buscamos todos los enlaces que contengan "/canales/" en su URL
        canal_links = await page.locator("a[href*='/canales/']").all()
        total_canales = len(canal_links)
        print(f"Se encontraron {total_canales} canales.")
        
        for i in range(total_canales):
            if i > 0:
                await page.goto(BASE_URL, wait_until="networkidle")
                await page.wait_for_selector("a[href*='/canales/']", timeout=30000)
            
            link = page.locator("a[href*='/canales/']").nth(i)
            nombre_canal = await link.inner_text()
            print(f"\nProcesando: {nombre_canal.strip()}")
            
            # Navegamos directamente a la URL del canal en lugar de hacer clic
            # (es más rápido y evita problemas con pestañas nuevas)
            href = await link.get_attribute("href")
            if not href.startswith("http"):
                href = "https://deporflix.pe" + href
            await page.goto(href, wait_until="networkidle")
            
            # 2. EXTRAER FUENTES DE VIDEO
            # Esperamos a que carguen las opciones (elementos con "OPCIÓN" en el texto)
            try:
                await page.wait_for_selector("text=/OPCIÓN/", timeout=15000)
            except:
                print(f"  -> No se encontraron opciones de video para {nombre_canal}.")
                continue
            
            # Buscamos los elementos que contienen las opciones
            opciones = await page.locator("text=/OPCIÓN/").all()
            
            if not opciones:
                print(f"  -> No tiene múltiples opciones. Buscando iframe directo...")
                iframe = page.locator("iframe").first
                src = await iframe.get_attribute("src")
                results[nombre_canal.strip()] = {"Única Opción": src}
            else:
                print(f"  -> Tiene {len(opciones)} opciones.")
                results[nombre_canal.strip()] = {}
                for j in range(len(opciones)):
                    # Hacemos clic en la opción j
                    btn = page.locator("text=/OPCIÓN/").nth(j)
                    nombre_opcion = await btn.inner_text()
                    await btn.click()
                    
                    # Esperamos a que el iframe cambie de src
                    await page.wait_for_timeout(2500)
                    
                    iframe = page.locator("iframe").first
                    src = await iframe.get_attribute("src")
                    results[nombre_canal.strip()][nombre_opcion.strip()] = src
                    print(f"     - {nombre_opcion.strip()}: {src}")
        
        await browser.close()
    
    # Guardar resultados
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Datos guardados en {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
