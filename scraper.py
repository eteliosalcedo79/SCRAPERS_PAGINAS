import asyncio
import json
from playwright.async_api import async_playwright

PELICULA_URL = "https://ganovideo.com/peliculas/hope-el-primer-impacto/"
OUTPUT_FILE = "resultados.json"

async def main():
    results = {}
    async with async_playwright() as p:
        # Prueba con headless=False si el sitio bloquea el modo headless
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print(f"Abriendo: {PELICULA_URL}", flush=True)
        try:
            await page.goto(PELICULA_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)  # Espera extra para JS

            # Estrategia 1: Buscar botones por selectores comunes de "servidores" o "opciones"
            # Ajusta estos selectores según lo que veas en el inspector de tu navegador
            posibles_selectores = [
                "a[href*='opcion']", "button:has-text('Opción')", 
                "div[class*='server']", "li[class*='option']",
                "text=Opción", "text=Servidor"
            ]
            
            botones = []
            for sel in posibles_selectores:
                try:
                    loc = page.locator(sel)
                    if await loc.count() > 0:
                        botones = await loc.all()
                        print(f"Botones encontrados con selector: {sel}", flush=True)
                        break
                except:
                    continue

            if not botones:
                print("No se encontraron botones con los selectores comunes.", flush=True)
                # Volcar HTML para depuración (opcional)
                # print(await page.content(), flush=True)
                return

            for i, btn in enumerate(botones):
                try:
                    nombre = (await btn.inner_text()).strip() or f"Opcion_{i+1}"
                    print(f"\n[{i+1}/{len(botones)}] Clic en: {nombre}", flush=True)
                    
                    await btn.click(timeout=5000)
                    
                    # Espera activa a que el iframe tenga un src válido
                    iframe = page.locator("iframe").first
                    src_anterior = await iframe.get_attribute("src") if await iframe.count() > 0 else None
                    
                    for _ in range(10):  # Intenta 10 veces (aprox. 5 seg)
                        await page.wait_for_timeout(500)
                        src_nuevo = await iframe.get_attribute("src") if await iframe.count() > 0 else None
                        if src_nuevo and src_nuevo != src_anterior:
                            results[nombre] = src_nuevo
                            print(f"  -> URL: {src_nuevo}", flush=True)
                            break
                    else:
                        print(f"  -> No se detectó cambio en el iframe.", flush=True)
                        
                except Exception as e:
                    print(f"  -> Error en '{nombre}': {e}", flush=True)
                await page.wait_for_timeout(1000)

        except Exception as e:
            print(f"Error general: {e}", flush=True)
        finally:
            await browser.close()
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Guardado en {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
