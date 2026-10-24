import re
from curl_cffi import requests

# URL de la película
MOVIE_URL = "https://cuevana3c.pro/pelicula/street-fighter-2"

def main():
    session = requests.Session(impersonate="chrome")
    print(f"1. Conectando a la película: {MOVIE_URL}")
    
    try:
        res_movie = session.get(MOVIE_URL, timeout=30)
        res_movie.raise_for_status()
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return

    html = res_movie.text
    print("✅ Página descargada con éxito.")

    print("\n2. Buscando los reproductores de 'Latino'...")

    # Estrategia: Buscar el div que contiene la palabra "Latino" y capturar la lista <ul> que le sigue
    latino_match = re.search(r'(?s)<div class="tab-item-name">\s*Latino.*?<ul>(.*?)</ul>', html)

    if latino_match:
        print("🎯 ¡Sección 'Latino' encontrada en el HTML!")
        
        # Extraemos el bloque de la lista
        bloque_latino = latino_match.group(1)
        
        # Buscamos todos los enlaces que estén dentro de data-server
        servidores = re.findall(r'data-server="([^"]+)"', bloque_latino)
        
        if servidores:
            print(f"\n✅ ¡Se encontraron {len(servidores)} reproductores Embed para Latino!\n")
            for i, url in enumerate(servidores, 1):
                print(f"   🎬 Opción {i}: {url}")
        else:
            print("⚠️ Se encontró la sección de Latino, pero no los enlaces 'data-server'.")
    else:
        print("❌ No se pudo encontrar la sección de 'Latino' en el HTML.")
        # Guardamos el HTML por si hay que depurar
        with open("debug_movie.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("👉 Se guardó 'debug_movie.html' para revisión.")

if __name__ == "__main__":
    main()
