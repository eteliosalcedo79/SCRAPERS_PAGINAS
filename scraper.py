import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://pirlotvapp.pro/", wait_until="networkidle")
        await page.wait_for_timeout(5000)

        print("--- INICIO HTML DEL EVENTO ---")
        # Buscamos el texto del partido y sacamos el código de su contenedor
        evento = page.locator("text=/ vs /i").first
        if await evento.count() > 0:
            # Imprimimos el HTML del cuadro gris (3 niveles arriba)
            contenedor = evento.locator("xpath=../../..")
            print(await contenedor.evaluate("el => el.outerHTML"))
        else:
            print("No se encontró evento")

        print("--- FIN HTML DEL EVENTO ---")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
