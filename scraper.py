import asyncio
import json
from playwright.async_api import async_playwright

# ⚠️ REEMPLAZA ESTO con la URL real de la página principal
BASE_URL = "https://tu-pagina-de-canales.com"
OUTPUT_FILE = "canales_iframes.json"

async def main():
    results = {}
    
    async with async_playwright() as p:
        # Lanzamos el navegador en modo headless (sin ventana)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"Abriendo página principal: {BASE_URL}")
        await page.goto(BASE_URL, wait_until="networkidle")
        
        # 1. EXTRAER ENLACES DE CANALES (Imagen 1)
        # ⚠️ Ajusta "a.boton-ver-canal" a la clase real de los botones verdes
        canal_links = await page.locator("a.boton-ver-canal").all()
        total_canales = len(canal_links)
        print(f"Se encontraron {total_canales} canales.")
        
        for i in range(total_canales):
            if i > 0:
                await page.goto(BASE_URL, wait_until="networkidle")
            
            # ⚠️ Ajusta los selectores según tu HTML
            link = page.locator("a.boton-ver-canal").nth(i)
            nombre_canal = await link.inner_text()
            print(f"\nProcesando: {nombre_canal}")
            await link.click()
            
            # Esperamos a que cargue la página del reproductor (Imagen 2)
            await page.wait_for_load_state("networkidle")
            
            # 2. EXTRAER FUENTES DE VIDEO (Imagen 2)
            # ⚠️ Ajusta "div.lista-fuentes button" a la clase real de las opciones
            opciones = await page.locator("div.lista-fuentes button").all()
            
            if not opciones:
                print(f"  -> No tiene múltiples opciones. Buscando iframe directo...")
                iframe = page.locator("iframe").first
                src = await iframe.get_attribute("src")
                results[nombre_canal] = {"Única Opción": src}
            else:
                print(f"  -> Tiene {len(opciones)} opciones.")
                results[nombre_canal] = {}
                for j in range(len(opciones)):
                    # Hacemos clic en la opción j
                    btn = page.locator("div.lista-fuentes button").nth(j)
                    nombre_opcion = await btn.inner_text()
                    await btn.click()
                    
                    # Esperamos un poco a que el iframe cambie de src
                    await page.wait_for_timeout(2000) 
                    
                    iframe = page.locator("iframe").first
                    src = await iframe.get_attribute("src")
                    results[nombre_canal][nombre_opcion] = src
                    print(f"     - {nombre_opcion}: {src}")
        
        await browser.close()
    
    # Guardar resultados
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Datos guardados en {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
