import json
import re
from curl_cffi import requests

BASE_URL = "https://pelisjuanita.com/tv/fox-sports"
LOGIN_URL = "https://pelisjuanita.com/inicio.php"
OUTPUT_FILE = "resultados_pelisjuanita.json"

def main():
    print("Iniciando sesión con huella de Chrome...")
    
    # Iniciamos una sesión que finge ser Chrome
    session = requests.Session(impersonate="chrome")
    
    # 1. Entramos a la página para recibir las cookies de Cloudflare
    print(f"Conectando a {BASE_URL}...")
    response = session.get(BASE_URL, timeout=30)
    
    # 2. Si nos pide login, lo hacemos
    if 'name="apodo"' in response.text:
        print("🔒 Pantalla de login detectada. Entrando como 'etelio'...")
        login_data = {"apodo": "etelio"}
        session.post(LOGIN_URL, data=login_data, timeout=30)
        
        # 3. Volvemos a pedir la página del canal ya logueados
        print("Navegando al canal...")
        response = session.get(BASE_URL, timeout=30)
        
    # Guardamos el HTML para ver qué pasó
    with open("debug_pagina.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("✅ HTML guardado en debug_pagina.html")
    
    # Buscamos los iframes
    iframes = re.findall(r'<iframe[^>]+src="([^"]+)"', response.text)
    print(f"Se encontraron {len(iframes)} iframes en la página.")
    
    resultados = {"FOX SPORTS": {}}
    for i, src in enumerate(iframes):
        print(f"✅ Encontrado: {src}")
        resultados["FOX SPORTS"][f"Reproductor_{i+1}"] = src
        
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Guardado en {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
