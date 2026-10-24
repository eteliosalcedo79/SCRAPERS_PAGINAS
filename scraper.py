import re
import json
from curl_cffi import requests
from urllib.parse import urljoin

# URL de la película
MOVIE_URL = "https://cuevana3c.pro/pelicula/street-fighter-2"
BASE_URL = "https://cuevana3c.pro/"

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
    
    # Guardamos el HTML por si acaso
    with open("debug_movie.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Guardado debug_movie.html")

    print("\n2. Buscando el bloque de servidores...")

    # En Cuevana/Dooplay, los servidores suelen estar en elementos <li> con atributos data-post, data-nume, data-type.
    li_blocks = re.findall(r'(?s)<li[^>]*data-post=["\']([^"\']+)["\'][^>]*>.*?</li>', html)
    
    if not li_blocks:
        li_blocks = re.findall(r'(?s)<li[^>]*data-post=["\']([^"\']+)["\'][^>]*>', html)

    if not li_blocks:
        print("⚠️ No se encontraron atributos 'data-post'. Volcando HTML para revisión...")
        match = re.search(r'(?s).{0,500}Latino.{0,500}', html, re.IGNORECASE)
        if match:
            print("👉 Encontramos esto cerca de 'Latino':")
            print(match.group(0))
        else:
            print("❌ Ni siquiera se encontró la palabra 'Latino' en el HTML.")
        return

    print(f"✅ Se encontraron {len(li_blocks)} botones de servidores en el HTML.")

    # Extraer los datos de cada servidor y filtrar el Latino
    server_items = re.findall(r'(?s)<li(.*?)</li>', html)
    
    for item in server_items:
        if 'data-post' not in item:
            continue
            
        post = re.search(r'data-post=["\']([^"\']+)["\']', item)
        nume = re.search(r'data-nume=["\']([^"\']+)["\']', item)
        type_ = re.search(r'data-type=["\']([^"\']+)["\']', item)
        
        # Extraer el texto del botón (donde dice Latino, Subtitulado, etc.)
        texto = re.sub(r'<[^>]+>', '', item).strip()
        texto = " ".join(texto.split())

        if post:
            post_id = post.group(1)
            nume_val = nume.group(1) if nume else "1"
            type_val = type_.group(1) if type_ else "movie"
            
            print(f"\n--- Servidor encontrado: {texto} ---")
            print(f"   POST: {post_id} | NUME: {nume_val} | TYPE: {type_val}")
            
            if "Latino" in texto or "Latino" in item:
                print("   🎯 ¡Este es el Latino! Simulando clic...")
                
                # La URL típica de peticiones AJAX en WordPress/Dooplay
                ajax_url = urljoin(BASE_URL, "/wp-admin/admin-ajax.php")
                payload = {
                    "action": "doo_player_ajax",
                    "post": post_id,
                    "nume": nume_val,
                    "type": type_val
                }
                
                try:
                    res_ajax = session.post(ajax_url, data=payload, timeout=15)
                    print(f"   📡 Respuesta del servidor: {res_ajax.status_code}")
                    
                    # Intentar leer como JSON
                    try:
                        json_data = res_ajax.json()
                        if "embed_url" in json_data:
                            embed_url = json_data["embed_url"]
                            print(f"   🎬 ¡IFRAME ENCONTRADO!: {embed_url}")
                            
                            # Si el embed_url trae código iframe, extraemos solo el src
                            src_match = re.search(r'src=["\']([^"\']+)["\']', embed_url)
                            if src_match:
                                print(f"   🔗 URL LIMPIA DEL REPRODUCTOR: {src_match.group(1)}")
                        else:
                            print(f"   ⚠️ JSON sin 'embed_url': {json_data}")
                    except:
                        print(f"   ⚠️ No es JSON. Respuesta cruda: {res_ajax.text[:300]}")
                        
                except Exception as e:
                    print(f"   ❌ Error en la petición AJAX: {e}")
                break # Detenerse después de encontrar el Latino

if __name__ == "__main__":
    main()
