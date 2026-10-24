import re
from curl_cffi import requests
from urllib.parse import urljoin

BASE_URL = "https://ganovideo.com/"

def main():
    session = requests.Session(impersonate="chrome")
    
    print("1. Conectando a la página principal...")
    res_home = session.get(BASE_URL, timeout=30)
    
    with open("debug_home.html", "w", encoding="utf-8") as f:
        f.write(res_home.text)
    print("✅ Guardado debug_home.html")

    # Buscar un enlace de película para visitar
    print("2. Buscando una película para analizar...")
    links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>', res_home.text)
    
    movie_url = None
    for link in links:
        # Ignorar enlaces de menús o categorías
        if any(x in link.lower() for x in ['/category/', '/tag/', '/page/', '/search', 'javascript:', '#']):
            continue
        full_url = urljoin(BASE_URL, link)
        # Si el enlace no es la página principal, lo tomamos como película
        if full_url != BASE_URL and len(full_url) > len(BASE_URL) + 2:
            movie_url = full_url
            break
            
    if not movie_url:
        print("❌ No se encontró ningún enlace de película automáticamente.")
        print("Por favor, edita el script y pon la URL exacta de una película en la variable movie_url.")
        return

    print(f"3. Entrando a la película: {movie_url}")
    res_movie = session.get(movie_url, timeout=30)
    
    with open("debug_movie.html", "w", encoding="utf-8") as f:
        f.write(res_movie.text)
    print("✅ Guardado debug_movie.html")

if __name__ == "__main__":
    main()
