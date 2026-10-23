import json
import re
import html
from curl_cffi import requests

BASE_URL = "https://pelisjuanita.com/tv/fox-sports"
LOGIN_URL = "https://pelisjuanita.com/inicio.php"
OUTPUT_FILE = "resultados_pelisjuanita.json"

def main():
    print("Iniciando sesión con huella de Chrome...")
    session = requests.Session(impersonate="chrome")
    
    # 1. Entramos a la página
    print(f"Conectando a {BASE_URL}...")
    response = session.get(BASE_URL, timeout=30)
    
    # 2. Login por si acaso
    if 'name="apodo"' in response.text:
        print("🔒 Haciendo login como 'etelio'...")
        session.post(LOGIN_URL, data={"apodo": "etelio"}, timeout=30)
        response = session.get(BASE_URL, timeout=30)
        
    html_content = response.text
    
    # Verificamos si Cloudflare nos bloqueó de nuevo
    if "Just a moment" in html_content:
        print("❌ Cloudflare nos ha bloqueado otra vez.")
        return

    print("✅ HTML obtenido. Extrayendo canales y servidores...")
    
    resultados = {}
    
    # 3. Magia pura: Buscamos los bloques de canales usando expresiones regulares
    # Buscamos el div con la clase "item" y capturamos lo que está dentro del onclick
    pattern = re.compile(r'<div class="item"[^>]*onclick="cambiarOpcion\(this, (\[.*?\])\)".*?<h2>(.*?)</h2>', re.DOTALL)
    matches = pattern.findall(html_content)
    
    for match in matches:
        json_servidores_raw = match[0]
        nombre_canal = match[1].strip()
        
        # Limpiamos el HTML para que sea un JSON válido
        json_servidores_raw = json_servidores_raw.replace('&quot;', '"')
        json_servidores_raw = html.unescape(json_servidores_raw) # Arregla cosas como &amp; a &
        
        try:
            # Convertimos el texto a una lista de diccionarios de Python
            servidores = json.loads(json_servidores_raw)
            
            if not servidores:
                continue
                
            resultados[nombre_canal] = {}
            
            # 4. Extraemos cada servidor
            for i, servidor in enumerate(servidores):
                url = servidor.get("url", "").strip()
                nombre_server = servidor.get("nombre", f"Servidor_{i+1}")
                
                # Si la URL es relativa (empieza con f.html), le ponemos el dominio
                if not url.startswith("http"):
                    url = "https://pelisjuanita.com/tv/" + url.lstrip("/")
                
                # Para no repetir nombres (porque todos se llaman "Servidor"), los numeramos
                nombre_final = f"{nombre_server} {i+1}"
                resultados[nombre_canal][nombre_final] = url
                
        except json.JSONDecodeError:
            print(f"⚠️ Error procesando servidores de {nombre_canal}")
            continue

    # 5. Guardar en el JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)
        
    print(f"✅ ¡Éxito total! Se extrajeron {len(resultados)} canales.")
    print(f"✅ Guardado en {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
