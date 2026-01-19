import json
import os
import re
import requests
from bs4 import BeautifulSoup

def limpiar_dato(texto):
    if not texto: return ""
    # SEPARAR FECHA Y HORA
    texto = re.sub(r'(\d{2}/\d{2}/\d{4})(\d{2}:\d{2})', r'\1 | \2', texto)
    return texto.replace('VS', '').strip()

def scrape_categoria(cat):
    slug = cat['slug']
    os.makedirs(slug, exist_ok=True)
    try:
        r = requests.get(cat['url'], timeout=20)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, "html.parser")
        matches = []
        for tr in soup.find_all("tr"):
            # Búsqueda flexible: cualquier variante de 3COM
            if "3com" in tr.get_text().lower():
                tds = tr.find_all("td")
                if len(tds) >= 4:
                    f = limpiar_dato(tds[0].get_text(strip=True))
                    l = limpiar_dato(tds[1].get_text(strip=True))
                    v = limpiar_dato(tds[2].get_text(strip=True))
                    res = limpiar_dato(tds[3].get_text(strip=True))
                    lug = limpiar_dato(tds[4].get_text(strip=True)) if len(tds) > 4 else ""
                    
                    # Corregir datos movidos en Territorial
                    if "-" in f and "/" in v:
                        matches.append({"fecha_texto": v, "local": l, "visitante": "3COM Squad Valsequillo", "resultado": f, "lugar": res})
                    else:
                        matches.append({"fecha_texto": f, "local": l, "visitante": v, "resultado": res, "lugar": lug})
        
        with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
            json.dump({"categoria": cat['name'], "matches": matches}, f, ensure_ascii=False, indent=2)
        print(f"✅ {cat['name']}: {len(matches)} partidos encontrados.")
    except Exception as e: print(f"❌ Error en {slug}: {e}")

def main():
    with open("categories.json", "r", encoding="utf-8") as f:
        categorias = json.load(f)
    for cat in categorias: scrape_categoria(cat)

if __name__ == "__main__": main()
