import asyncio
import json
from playwright.async_api import async_playwright

SITE_ROOT = "https://pelotalibre.biz"
AGENDA_URL = f"{SITE_ROOT}/agenda"
OUTPUT_FILE = "eventos_pelotalibre.json"

async def get_embeds_from_match_page(context, match_url, match_name):
    """Paso 2 y 3: Entra a la página del partido y extrae los iframes de cada fuente."""
    page = await context.new_page()
    embeds = []
    try:
        await page.goto(match_url, wait_until="domcontentloaded", timeout=30000)
        # Esperar a que la página cargue el contenedor del reproductor
        await page.wait_for_timeout(3000) 

        # Buscamos los botones de las fuentes. 
        # Basado en la imagen 4, los botones contienen el texto "FUENTE"
        # (Ajusta este selector si es necesario, por ejemplo: '.source-btn', 'a:has-text("FUENTE")', etc.)
        source_buttons = page.locator('button:has-text("FUENTE"), a:has-text("FUENTE"), div:has-text("FUENTE")')
        
        count = await source_buttons.count()
        
        if count == 0:
            # Si no hay botones de fuente, intentamos sacar el iframe por defecto
            try:
                await page.wait_for_selector("iframe", state="attached", timeout=5000)
                iframe = page.locator("iframe").first
                src = await iframe.get_attribute("src") or await iframe.get_attribute("data-src")
                if src:
                    embeds.append({"fuente": "Por defecto", "url": src})
            except Exception:
                pass
            return embeds

        print(f"      Encontradas {count} fuentes. Extrayendo...")

        for i in range(count):
            btn = source_buttons.nth(i)
            try:
                # Obtenemos el nombre de la fuente (ej. "FUENTE 1 ESPN 2")
                source_name = await btn.inner_text()
                source_name = source_name.strip().replace("\n", " ")

                # Hacemos clic en la fuente
                await btn.click()
                
                # Esperamos un poco a que el iframe se actualice
                await page.wait_for_timeout(2500)
                
                # Extraemos el src del iframe actual
                iframe = page.locator("iframe").first
                src = await iframe.get_attribute("src")
                
                if not src or src.strip() == "":
                    src = await iframe.get_attribute("data-src")
                    
                if src and not any(e["url"] == src for e in embeds):
                    embeds.append({"fuente": source_name, "url": src})
                    
            except Exception as e:
                print(f"        ⚠️ Error al extraer fuente {i+1}: {e}")
                
        return embeds

    except Exception as e:
        print(f"      ❌ Error general en la página del partido: {e}")
        return embeds
    finally:
        await page.close()


async def main():
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        print(f"Abriendo agenda: {AGENDA_URL}")
        await page.goto(AGENDA_URL, wait_until="networkidle", timeout=60000)

        # --- PASO 1: Extraer eventos de la agenda ---
        print("Buscando eventos en la agenda...")
        
        # Primero, desplegamos todos los acordeones haciendo clic en las flechas o en los eventos.
        # Asumiendo que hay botones con flechas o que al hacer clic en el título se abre.
        # Vamos a intentar extraer los enlaces directamente si están en el HTML oculto:
        
        # Buscamos todos los enlaces que digan "Abrir partido"
        # Si el texto exacto varía, cambia 'Abrir partido' por la clase CSS correspondiente
        match_links = await page.locator('a:has-text("Abrir partido")').all()
        
        # Si no los encuentra directamente, hay que interactuar con los acordeones:
        if not match_links:
            print("No se encontraron enlaces directos. Expandiendo acordeones...")
            # Buscar los elementos que despliegan el acordeón (ej. las flechas a la derecha)
            toggles = await page.locator('.event-item .toggle-icon, .match-row').all() # Ajusta este selector
            for toggle in toggles:
                try:
                    await toggle.click()
                    await page.wait_for_timeout(500)
                except:
                    pass
            
            # Volvemos a buscar los enlaces ahora que están visibles
            match_links = await page.locator('a:has-text("Abrir partido")').all()

        total_partidos = len(match_links)
        print(f"Se encontraron {total_partidos} partidos para procesar.")

        # --- PASO 2: Iterar sobre cada partido ---
        for i, link in enumerate(match_links):
            try:
                # Intentamos obtener el nombre del partido. 
                # Subimos al contenedor padre del enlace para buscar el título.
                # (Ajusta el selector si es necesario)
                parent = link.locator('xpath=ancestor::div[contains(@class, "event") or contains(@class, "match")][1]')
                try:
                    match_name = await parent.locator('.event-title, .match-title').first.inner_text()
                    match_name = match_name.strip()
                except:
                    match_name = f"Partido {i+1}"

                print(f"\n[{i+1}/{total_partidos}] Procesando: {match_name}")

                # Obtener la URL del partido
                href = await link.get_attribute("href")
                if not href:
                    # Si es un botón que usa JavaScript, hacemos clic y obtenemos la URL
                    await link.click()
                    await page.wait_for_load_state("domcontentloaded")
                    match_url = page.url
                    await page.go_back() # Volvemos a la agenda para el siguiente
                else:
                    match_url = href if href.startswith("http") else f"{SITE_ROOT}{href}"

                # Extraer los embeds de la página del partido
                embeds = await get_embeds_from_match_page(context, match_url, match_name)
                
                # Guardar en el diccionario general
                if match_name in results:
                    match_name = f"{match_name} ({i+1})"
                results[match_name] = embeds
                
                if embeds:
                    print(f"     ✅ {len(embeds)} embeds encontrados.")
                else:
                    print(f"     ❌ No se encontraron embeds.")

            except Exception as e:
                print(f"  ❌ Error procesando el partido {i+1}: {e}")

        await browser.close()

    # Guardar resultados
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Datos guardados en {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
